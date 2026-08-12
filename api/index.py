import subprocess
import sys
from streamlit.web import cli as stcli

# Download spaCy model on startup
try:
    import spacy
    spacy.load("en_core_web_sm")
except:
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])

def run():
    sys.argv = ["streamlit", "run", "app.py", "--server.port=3000", "--server.address=0.0.0.0"]
    stcli.main()

if __name__ == "__main__":
    run()
