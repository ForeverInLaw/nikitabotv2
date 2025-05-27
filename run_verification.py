import asyncio
import logging
import sys
import os

# Explicitly add /app to sys.path
# This is to ensure that 'app.module' imports work correctly
# irrespective of how Python's path is being initialized by the environment.
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

# Further, ensure the parent of 'app' is on the path for 'from app...' imports
# if the script is being run as /app/run_verification.py
# In this sandbox, /app is the repo root. So effectively, we need '/' on the path
# for 'from app...' to work if 'app' is treated as a package.
# Let's add the parent of the script's directory if 'app' is not directly found.
# The script is /app/run_verification.py. os.path.dirname(__file__) is /app.
# os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) is /.
script_dir_parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if script_dir_parent not in sys.path:
     sys.path.insert(0, script_dir_parent)


from app.db.database import init_db, close_db, get_session
from app.db.repositories.product_repo import ProductRepository
from app.schemas.product_schemas import ManufacturerCreate
from config.settings import settings # This should be found if /app is in sys.path (config is /app/config)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info(f"Script CWD: {os.getcwd()}")
    logger.info(f"Python sys.path before execution: {sys.path}") # Log path after our changes
    logger.info("Initializing database connection...")
    await init_db(settings)

    manufacturer_name = "TestManufacturerSysPathFix"
    created_manufacturer_id: int | None = None

    try:
        async with get_session() as session:
            product_repo = ProductRepository(session)

            logger.info(f"Attempting to create manufacturer: {manufacturer_name}")
            manufacturer_data = ManufacturerCreate(name=manufacturer_name)

            try:
                created_manufacturer_model = await product_repo.create_manufacturer(manufacturer_data)
                created_manufacturer_id = created_manufacturer_model.id
                logger.info(f"Successfully created manufacturer: ID={created_manufacturer_model.id}, Name={created_manufacturer_model.name}")
                logger.info(f"Created_at: {created_manufacturer_model.created_at}, Updated_at: {created_manufacturer_model.updated_at}")

                if created_manufacturer_model.created_at is None or created_manufacturer_model.updated_at is None:
                    logger.error("ERROR: created_at or updated_at is None after creation!")
                    raise ValueError("Timestamp fields are None after creation.")
                else:
                    logger.info("SUCCESS: Timestamp fields are present and not None.")

            except Exception as e:
                logger.error(f"Error during manufacturer creation: {e}", exc_info=True)
                created_manufacturer_id = None 
                raise 

            if created_manufacturer_id is not None:
                logger.info(f"Attempting to delete manufacturer with ID: {created_manufacturer_id}")
                try:
                    success = await product_repo.delete_manufacturer_by_id(created_manufacturer_id)
                    if success:
                        logger.info(f"Successfully deleted manufacturer with ID: {created_manufacturer_id}")
                    else:
                        logger.error(f"Failed to delete manufacturer with ID: {created_manufacturer_id}.")
                except Exception as e:
                    logger.error(f"Error during manufacturer deletion: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Verification script failed: {e}", exc_info=True)
        # For the final report, this indicates failure
        # To make the calling environment aware, exit with a non-zero code
        sys.exit(1) 
    finally:
        logger.info("Closing database connection...")
        await close_db()
        logger.info("Database connection closed.")

if __name__ == "__main__":
    asyncio.run(main())
