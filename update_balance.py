import logging
from rating_manager import RatingManager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def update_balances():
    """Установить баланс всех пользователей в 100 000 очков"""
    rating_manager = RatingManager()
    
    count = 0
    total_points = 0
    
    logger.info("Starting balance update...")
    
    for chat_id, users in rating_manager.ratings.items():
        for user_id in users:
            # Устанавливаем баланс
            rating_manager.ratings[chat_id][user_id] = 100000
            count += 1
            total_points += 100000
            
    rating_manager.save_ratings()
    logger.info(f"Updated {count} users. Total points in system: {total_points}")
    print(f"✅ Successfully set balance to 100,000 for {count} users!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        update_balances()
    else:
        confirm = input("Are you sure you want to set EVERY user's balance to 100,000? (yes/no): ")
        if confirm.lower() == 'yes':
            update_balances()
        else:
            print("Operation cancelled.")
