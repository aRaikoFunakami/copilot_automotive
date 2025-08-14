# setup.sh
if [ ! -d "tmdb_agent" ]; then
    git clone https://github.com/aRaikoFunakami/tmdb_agent.git
fi
uv add --editable ./tmdb_agent