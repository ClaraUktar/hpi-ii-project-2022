from epo_crawler.epo_extractor import EpoExtractor
from dotenv import load_dotenv

def run():
    load_dotenv()
    EpoExtractor().extract()

if __name__ == "__main__":
    run()