import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from house_protocol.settings import load_settings

logger = logging.getLogger(__name__)



def heartbeat() -> None:
    logger.info("alive mi amigo")

def main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level = settings.log_level,
        format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    
    logger.info("starting scheduler, data_dir%s", settings.data_dir)
    
    scheduler = BlockingScheduler(timezone = "UTC")
    scheduler.add_job(heartbeat, "interval", minutes = 1)
    scheduler.start()
    
    
if __name__ == "__main__":
    main()