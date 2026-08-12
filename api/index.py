from streamlit.web import cli as stcli
import sys

def run():
    sys.argv = ["streamlit", "run", "app.py", "--server.port=3000", "--server.address=0.0.0.0"]
    stcli.main()

if __name__ == "__main__":
    run()
