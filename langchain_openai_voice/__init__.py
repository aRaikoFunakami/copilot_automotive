import asyncio
import json
import websockets
import logging

from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator, Any, Callable, Coroutine
from langchain_openai_voice.utils import amerge

from langchain_core.tools import BaseTool
from langchain_core._api import beta
from langchain_core.utils import secret_from_env

from pydantic import BaseModel, Field, SecretStr, PrivateAttr

DEBUG_BY_WSCAT = False


DEFAULT_MODEL = "gpt-4o-realtime-preview-2024-10-01"
DEFAULT_URL = "wss://api.openai.com/v1/realtime"

EVENTS_TO_IGNORE = {
    "response.function_call_arguments.delta",
    "rate_limits.updated",
    "response.audio_transcript.delta",
    "response.created",
    "response.content_part.added",
    "response.content_part.done",
    "conversation.item.created",
    "response.audio.done",
    "session.created",
    "session.updated",
    "response.done",
    "response.output_item.done",
    "response.text.delta",
    "response.output_item.added",
}

RESPONSE_CREATE_TEXT = {
    "type": "response.create",
    "event_id": "text_event",
    "response": {
        "modalities": ["text"],
        "instructions": "Please respond by text.",
    },
    
}

RESPONSE_CREATE_AUDIO = {
    "type": "response.create",
    "event_id": "audio_event",
    "response": {
        "modalities": ["text", "audio"],
        "instructions": "Please respond by audio.",
        "voice": "sage",
    },
}



@asynccontextmanager
async def connect(*, api_key: str, model: str, url: str) -> AsyncGenerator[
    tuple[
        Callable[[dict[str, Any] | str], Coroutine[Any, Any, None]],
        AsyncIterator[dict[str, Any]],
    ],
    None,
]:
    """
    async with connect(model="gpt-4o-realtime-preview-2024-10-01") as websocket:
        await websocket.send("Hello, world!")
        async for message in websocket:
            print(message)
    """

    headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "realtime=v1",
    }

    url = url or DEFAULT_URL
    url += f"?model={model}"

    websocket = await websockets.connect(url, extra_headers=headers)

    try:

        async def send_event(event: dict[str, Any] | str) -> None:
            formatted_event = json.dumps(event) if isinstance(event, dict) else event
            await websocket.send(formatted_event)

        async def event_stream() -> AsyncIterator[dict[str, Any]]:
            async for raw_event in websocket:
                yield json.loads(raw_event)

        stream: AsyncIterator[dict[str, Any]] = event_stream()

        yield send_event, stream
    finally:
        await websocket.close()


class VoiceToolExecutor(BaseModel):
    """
    Can accept function calls and emits function call outputs to a stream.
    """

    tools_by_name: dict[str, BaseTool]
    _trigger_future: asyncio.Future = PrivateAttr(default_factory=asyncio.Future)
    _lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)

    async def _trigger_func(self) -> dict:
        """
        Wait until set_result() is called, then return tool_call.
        """
        return await self._trigger_future

    async def add_tool_call(self, tool_call: dict) -> None:
        """
        The tool is executed triggered by the function_call_arguments.done event received from the model side.
        """
        async with self._lock:
            if self._trigger_future.done():
                # TODO: handle simultaneous tool calls better
                raise ValueError("Tool call adding already in progress")

            self._trigger_future.set_result(tool_call)

    async def _create_tool_call_task(self, tool_call: dict) -> asyncio.Task:
        """
        実際にツールを呼び出すためのタスクを作成し、結果をまとめて返す。
        """
        tool = self.tools_by_name.get(tool_call["name"])
        if tool is None:
            raise ValueError(
                f"tool {tool_call['name']} not found. "
                f"Must be one of {list(self.tools_by_name.keys())}"
            )

        # try to parse args
        try:
            args = json.loads(tool_call["arguments"])
        except json.JSONDecodeError:
            raise ValueError(
                f"failed to parse arguments `{tool_call['arguments']}`. Must be valid JSON."
            )

        async def run_tool() -> dict:
            result = await tool.ainvoke(args)
            try:
                result_str = json.dumps(result)
            except TypeError:
                # not json serializable, use str
                result_str = str(result)
            return {
                "type": "conversation.item.create",
                "item": {
                    "id": tool_call["call_id"],
                    "call_id": tool_call["call_id"],
                    "type": "function_call_output",
                    "output": result_str,
                },
            }

        task = asyncio.create_task(run_tool())
        return task

    async def output_iterator(self) -> AsyncIterator[dict]:
        """
        Stream of tool execution results
        """
        trigger_task = asyncio.create_task(self._trigger_func())
        tasks = set([trigger_task])

        while True:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                tasks.remove(task)
                if task == trigger_task:
                    # Regenerate Future for the next trigger.
                    async with self._lock:
                        self._trigger_future = asyncio.Future()
                    trigger_task = asyncio.create_task(self._trigger_func())
                    tasks.add(trigger_task)
                    tool_call = task.result()
                    try:
                        new_task = await self._create_tool_call_task(tool_call)
                        tasks.add(new_task)
                    except ValueError as e:
                        yield {
                            "type": "conversation.item.create",
                            "item": {
                                "id": tool_call["call_id"],
                                "call_id": tool_call["call_id"],
                                "type": "function_call_output",
                                "output": (f"Error: {str(e)}"),
                            },
                        }
                else:
                    # Return the results of the tool execution as it is.
                    yield task.result()


@beta()
class OpenAIVoiceReactAgent(BaseModel):
    """
    Voice+Tools-enabled agents using the OpenAI Realtime API.
    Further functionality added to support text input.
    """

    model: str
    api_key: SecretStr = Field(
        alias="openai_api_key",
        default_factory=secret_from_env("OPENAI_API_KEY", default=""),
    )
    instructions: str | None = None
    tools: list[BaseTool] | None = None
    url: str = Field(default=DEFAULT_URL)

    async def aconnect(
        self,
        input_stream: AsyncIterator[str],
        send_output_chunk: Callable[[str], Coroutine[Any, Any, None]],
    ) -> None:
        """
        Connect to the OpenAI API and send and receive messages.

        input_stream: AsyncIterator[str]
            Stream of input events to send to the model. Usually transports input_audio_buffer.append events from the microphone.
        output: Callable[[str], None]
            Callback to receive output events from the model. Usually sends response.audio.delta events to the speaker.

        """
        # formatted_tools: list[BaseTool] = [
        #     tool if isinstance(tool, BaseTool) else tool_converter.wr(tool)  # type: ignore
        #     for tool in self.tools or []
        # ]
        tools_by_name = {tool.name: tool for tool in self.tools or []}
        tool_executor = VoiceToolExecutor(tools_by_name=tools_by_name)

        async with connect(
            model=self.model, api_key=self.api_key.get_secret_value(), url=self.url
        ) as (
            model_send,
            model_receive_stream,
        ):
            # sent tools and instructions with initial chunk
            tool_defs = [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {"type": "object", "properties": tool.args},
                }
                for tool in tools_by_name.values()
            ]
            await model_send(
                {
                    "type": "session.update",
                    "session": {
                        "instructions": self.instructions,
                        "input_audio_transcription": {
                            "model": "whisper-1",
                        },
                        "tools": tool_defs,
                        "voice": "sage",
                    },
                }
            )

            def is_input_text(role: str, data: dict) -> bool:
                if not role in ["user", "assistant", "system"]:
                    logging.error(f"Invalid role: {role}")
                    return False
                
                if "item" in data and "content" in data["item"] and "role" in data["item"]:
                    if data["item"]["role"] != role:
                        return False
                    
                    for content in data["item"]["content"]:
                        if content.get("type") == "input_text":
                            return True
                return False
            
            # amerge to bring together 3 streams.
            # 1. input_mic=input_stream (voice or text)
            # 2. output_speaker=model_receive_stream (response from OpenAI)
            # 3. tool_outputs=tool_executor.output_iterator() (results of tool execution)
            async for stream_key, data_raw in amerge(
                input_mic=input_stream,
                output_speaker=model_receive_stream,
                tool_outputs=tool_executor.output_iterator(),
            ):
                # First attempt JSON decoding. If unsuccessful, process as ‘raw text input’.
                try:
                    data = (
                        json.loads(data_raw) if isinstance(data_raw, str) else data_raw
                    )
                except json.JSONDecodeError:
                    # Interpreted as text input
                    logging.error("Ignore received raw text input: %s", data_raw)
                    continue

                # When text input is received from the client
                if stream_key == "input_mic" and (is_input_text("user", data) or is_input_text("system", data)):
                    stream_key = "input_text"


                if stream_key == "input_mic":
                    logging.info(f"stream_key:{stream_key} data:{json.dumps(data, indent=2, ensure_ascii=False)[:100]}")
                    await model_send(data)

                elif stream_key == "input_text":
                    await model_send(data)
                    logging.info(f"stream_key:{stream_key} data:{json.dumps(data, indent=2, ensure_ascii=False)}")
                    await asyncio.sleep(0.1)

                    # Send ‘response.create’ to generate a text response
                    if is_input_text("user", data):
                        if DEBUG_BY_WSCAT:
                            event = RESPONSE_CREATE_TEXT
                        else:
                            event = RESPONSE_CREATE_AUDIO
                    else: 
                        event = RESPONSE_CREATE_TEXT
                    logging.info("Sending response.create for text input: %s", json.dumps(event, indent=2, ensure_ascii=False))
                    await model_send(event)

                elif stream_key == "tool_outputs":
                    # Returns the results of the tool execution to both model + client
                    logging.info(f"stream_key:{stream_key} data:{json.dumps(data, indent=2, ensure_ascii=False)}")
                    await model_send(data)
                    if DEBUG_BY_WSCAT:
                        await model_send(RESPONSE_CREATE_TEXT)
                    else:
                        await model_send(RESPONSE_CREATE_AUDIO)
                    

                    # If the output from the tool contains ‘return_direct’: True, it can be displayed to the client as it is, etc.
                    t = data["type"]
                    if t == "conversation.item.create":
                        output_str = data["item"].get("output", "")
                        try:
                            output_json = json.loads(output_str)
                            print(f"★★★　output_json: {json.dumps(output_json, indent=2, ensure_ascii=False)}")
                            if isinstance(output_json, dict):
                                return_direct = output_json.get("return_direct", False)
                                if return_direct:
                                    await send_output_chunk(output_str)
                        except Exception:
                            pass

                elif stream_key == "output_speaker":
                    # Process response from OpenAI
                    t = data["type"]
                    if t == "response.audio.delta":
                        # Send audio stream to the client
                        await send_output_chunk(json.dumps(data))
                    elif t == "response.audio_buffer.speech_started":
                        # Audio playback start timing
                        await send_output_chunk(json.dumps(data))
                    elif t == "error":
                        logging.error("error: %s", json.dumps(data, indent=2, ensure_ascii=False))
                    elif t == "response.function_call_arguments.done":
                        # Execute the tool when the final argument for the tool call is received
                        logging.info("function_call: %s", json.dumps(data, indent=2, ensure_ascii=False))
                        await tool_executor.add_tool_call(data)
                    elif t == "response.audio_transcript.done":
                        # When Whisper (speech recognition) is completed
                        # logging.info("model(audio transcript): %s", json.dumps(data["transcript"], indent=2, ensure_ascii=False))
                        pass
                    elif t == "conversation.item.input_audio_transcription.completed":
                        # Transcript when microphone input is completed
                        logging.info("user(audio): %s", json.dumps(data["transcript"], indent=2, ensure_ascii=False))
                    elif t == "response.text.done":
                        # Text response is completed, send it to the client
                        logging.info("response.text.done: %s", json.dumps(data, indent=2, ensure_ascii=False))
                        response_text = data.get("text", "")
                        await send_output_chunk(response_text)
                    elif t in EVENTS_TO_IGNORE:
                        # Events to ignore
                        pass
                    elif t == "input_audio_buffer.speech_started":
                        logging.warning("input_audio_buffer.speech_started.\n Consider handling interruptions or other processes on the client side")
                    else:
                        logging.error("Unhandled event type: %s", t)

__all__ = ["OpenAIVoiceReactAgent"]