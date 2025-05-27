import logging
import sys
from sqlalchemy import create_engine, text, exc

# Attempt to import settings. This is the only project-specific import.
# If this fails, the PYTHONPATH/module setup is fundamentally broken for any script.
try:
    from config.settings import settings
except ModuleNotFoundError:
    print("CRITICAL: Could not import 'config.settings'. Ensure PYTHONPATH is correct or script is run from a location where 'config' module is visible.", file=sys.stderr)
    sys.path.insert(0, '/app') # Try to forcibly add /app to path
    try:
        from config.settings import settings
        print("INFO: Successfully imported 'config.settings' after path adjustment.")
    except ModuleNotFoundError:
        print("CRITICAL: Still could not import 'config.settings' after path adjustment. Aborting.", file=sys.stderr)
        sys.exit(2) # Specific exit code for config import failure


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Use the synchronous database URL
DATABASE_URL = settings.DATABASE_URL_SYNC

def main():
    logger.info(f"Attempting DB timestamp verification using database URL: {DATABASE_URL[:DATABASE_URL.rfind(':')]}...") # Hide password
    engine = None
    script_failed = False
    manufacturer_name = "DirectSQLTimestampTest"
    inserted_id = None

    try:
        engine = create_engine(DATABASE_URL)
        
        logger.info("Attempting to connect to the database...")
        with engine.connect() as connection: # Test connection
            logger.info("Successfully connected to the database.")
            # SQLAlchemy connections might start transactions implicitly depending on DBAPI.
            # Explicitly commit to ensure the connection test itself doesn't leave a transaction open.
            connection.commit() 

        # Use a new session for operations
        with engine.connect() as connection:
            try:
                # 1. Insert a new manufacturer
                logger.info(f"Attempting to insert manufacturer: {manufacturer_name}")
                # Use RETURNING to get values back, including defaults
                insert_query = text("INSERT INTO manufacturers (name) VALUES (:name) RETURNING id, created_at, updated_at;")
                result = connection.execute(insert_query, {"name": manufacturer_name})
                inserted_row = result.fetchone()
                connection.commit() # Commit the insert

                if inserted_row:
                    inserted_id = inserted_row[0] # Corrected index for id
                    created_at_val = inserted_row[1] # Corrected index for created_at
                    updated_at_val = inserted_row[2] # Corrected index for updated_at
                    logger.info(f"Successfully inserted manufacturer: ID={inserted_id}, Name={manufacturer_name}")
                    logger.info(f"DB returned Created_at: {created_at_val}, Updated_at: {updated_at_val}")

                    if created_at_val is None or updated_at_val is None:
                        logger.error("ERROR: Database returned None for created_at or updated_at!")
                        script_failed = True
                    else:
                        logger.info("SUCCESS: created_at and updated_at columns are populated by the database.")
                else:
                    logger.error("ERROR: Failed to insert manufacturer or retrieve the inserted row.")
                    script_failed = True

            except exc.DBAPIError as e: # Catches UndefinedColumnError, ProgrammingError etc.
                logger.error(f"Database error during insert/query: {e}", exc_info=True)
                if "undefined column" in str(e).lower() and \
                   ("created_at" in str(e).lower() or "updated_at" in str(e).lower()):
                    logger.error("VERIFICATION FAILED: Specific UndefinedColumnError for timestamps caught!")
                script_failed = True
            except Exception as e:
                logger.error(f"An unexpected error occurred during DB operations: {e}", exc_info=True)
                script_failed = True
            finally:
                if inserted_id and not script_failed: # Only delete if insert was successful and no critical error occurred
                    try:
                        logger.info(f"Attempting to delete test manufacturer with ID: {inserted_id}")
                        delete_query = text("DELETE FROM manufacturers WHERE id = :id;")
                        connection.execute(delete_query, {"id": inserted_id})
                        connection.commit() # Commit the delete
                        logger.info(f"Successfully deleted test manufacturer ID: {inserted_id}")
                    except Exception as e:
                        logger.error(f"Error during manufacturer deletion: {e}", exc_info=True)
                        # Not marking script_failed=True for deletion failure, as main test might have passed.
                
                # Connection automatically closed by 'with' block

    except Exception as e: # Catch errors like connection failure to the engine itself
        logger.error(f"A critical error occurred (e.g., DB connection, engine setup): {e}", exc_info=True)
        script_failed = True
    finally:
        if engine:
            engine.dispose()
            logger.info("Database engine disposed.")

    if script_failed:
        logger.error("DB timestamp verification FAILED.")
        sys.exit(1) # Exit with error code
    else:
        logger.info("DB timestamp verification SUCCEEDED.")
        sys.exit(0) # Exit with success code

if __name__ == "__main__":
    main()
