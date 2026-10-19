
import logging

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,  # change to DEBUG in dev
        format= "%(asctime)s -  %(levelname)s - %(name)s  -  %(message)s"
    )

def get_logger(name: str):
    return logging.getLogger(name)
