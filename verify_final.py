import asyncio
import logging
import sys
import os

# This script assumes it's run from /app (the CWD of the tool)
# and that /app is effectively the root for these module lookups.

# Ensure /app is in sys.path, just in case CWD isn't added as expected.
if '/app' not in sys.path:
    sys.path.insert(0, '/app')


from db.database import init_db, close_db, get_session
from db.repositories.product_repo import ProductRepository
from schemas.product_schemas import ManufacturerCreate
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info(f"Script CWD: {os.getcwd()} - should be /app")
    logger.info(f"Python sys.path: {sys.path}")
    logger.info("Initializing database connection...")
    await init_db(settings)

    manufacturer_name = "TestManufacturerFinalAttempt"
    created_manufacturer_id: int | None = None
    script_failed = False

    try:
        async with get_session() as session:
            product_repo = ProductRepository(session)

            logger.info(f"Attempting to create manufacturer: {manufacturer_name}")
            manufacturer_data = ManufacturerCreate(name=manufacturer_name)

            try:
                created_manufacturer_model = await product_repo.create_manufacturer(manufacturer_data)
                created_manufacturer_id = created_manufacturer_model.id
                logger.info(f"Successfully created manufacturer: ID={created_manufacturer_model.id}, Name={created_manufacturer_model.name}")
                
                # THE CRITICAL CHECK:
                created_at_value = created_manufacturer_model.created_at
                updated_at_value = created_manufacturer_model.updated_at
                logger.info(f"Created_at: {created_at_value}, Updated_at: {updated_at_value}")

                if created_at_value is None or updated_at_value is None:
                    logger.error("ERROR: created_at or updated_at is None after creation!")
                    script_failed = True # Mark failure
                else:
                    logger.info("SUCCESS: Timestamp fields are present and not None.")

            except Exception as e:
                logger.error(f"Error during manufacturer creation: {e}", exc_info=True)
                created_manufacturer_id = None 
                script_failed = True # Mark failure
                # No re-raise here, allow finally block to run, then sys.exit based on script_failed

            if created_manufacturer_id is not None:
                logger.info(f"Attempting to delete manufacturer with ID: {created_manufacturer_id}")
                try:
                    success = await product_repo.delete_manufacturer_by_id(created_manufacturer_id)
                    if success:
                        logger.info(f"Successfully deleted manufacturer with ID: {created_manufacturer_id}")
                    else:
                        logger.error(f"Failed to delete manufacturer with ID: {created_manufacturer_id}. This is a cleanup issue but main test might have passed.")
                        # Not setting script_failed = True here as the main test is about creation.
                except Exception as e:
                    logger.error(f"Error during manufacturer deletion: {e}", exc_info=True)
                    # Also not setting script_failed = True here for same reason.

    except Exception as e:
        logger.error(f"A critical error occurred in the script: {e}", exc_info=True)
        script_failed = True
    finally:
        logger.info("Closing database connection...")
        await close_db()
        logger.info("Database connection closed.")
    
    if script_failed:
        logger.error("Verification script FAILED.")
        sys.exit(1) # Exit with error code
    else:
        logger.info("Verification script SUCCEEDED.")
        sys.exit(0) # Exit with success code

if __name__ == "__main__":
    asyncio.run(main())
