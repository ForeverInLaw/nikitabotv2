import asyncio
import logging
from sqlalchemy import create_engine, text, exc
from sqlalchemy.orm import sessionmaker
from config.settings import settings  # Assuming this can be imported if /app is in PYTHONPATH or script is in /app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use the synchronous database URL for this direct SQLAlchemy script
DATABASE_URL = settings.DATABASE_URL_SYNC  # e.g., "postgresql://user:pass@host/db"

async def main():
    logger.info(f"Using database URL: {DATABASE_URL}")
    engine = None
    script_failed = False
    manufacturer_name = "DirectSQLTestManufacturer"
    inserted_id = None

    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        logger.info("Attempting to connect to the database...")
        with engine.connect() as connection:
            logger.info("Successfully connected to the database.")
            connection.commit() # End any implicit transaction from connect if any

        session = SessionLocal()
        logger.info("Database session started.")

        try:
            # 1. Insert a new manufacturer using raw SQL, only providing 'name'
            logger.info(f"Attempting to insert manufacturer: {manufacturer_name}")
            insert_query = text("INSERT INTO manufacturers (name) VALUES (:name) RETURNING id, created_at, updated_at;")
            result = session.execute(insert_query, {"name": manufacturer_name})
            inserted_row = result.fetchone()
            session.commit()

            if inserted_row:
                inserted_id = inserted_row[0]
                created_at_val = inserted_row[1]
                updated_at_val = inserted_row[2]
                logger.info(f"Successfully inserted manufacturer: ID={inserted_id}, Name={manufacturer_name}")
                logger.info(f"DB returned Created_at: {created_at_val}, Updated_at: {updated_at_val}")

                if created_at_val is None or updated_at_val is None:
                    logger.error("ERROR: Database returned None for created_at or updated_at!")
                    script_failed = True
                else:
                    logger.info("SUCCESS: created_at and updated_at columns are populated by the database.")
            else:
                logger.error("ERROR: Failed to insert manufacturer or retrieve row.")
                script_failed = True

        except exc.DBAPIError as e: # Catches UndefinedColumnError among others
            logger.error(f"Database error during insert/query: {e}", exc_info=True)
            if "undefined column" in str(e).lower() and ("created_at" in str(e).lower() or "updated_at" in str(e).lower()):
                logger.error("Specific UndefinedColumnError for timestamps caught!")
            script_failed = True
        except Exception as e:
            logger.error(f"An unexpected error occurred during DB operations: {e}", exc_info=True)
            script_failed = True
        finally:
            if inserted_id and not script_failed: # Only attempt delete if insert seemed okay and no other critical error
                try:
                    logger.info(f"Attempting to delete manufacturer with ID: {inserted_id}")
                    delete_query = text("DELETE FROM manufacturers WHERE id = :id;")
                    session.execute(delete_query, {"id": inserted_id})
                    session.commit()
                    logger.info(f"Successfully deleted test manufacturer ID: {inserted_id}")
                except Exception as e:
                    logger.error(f"Error during manufacturer deletion: {e}", exc_info=True)
                    # Don't mark script_failed for deletion issues if main test passed
            
            session.close()
            logger.info("Database session closed.")

    except Exception as e:
        logger.error(f"A critical error occurred (e.g., connection, setup): {e}", exc_info=True)
        script_failed = True
    finally:
        if engine:
            engine.dispose()
            logger.info("Database engine disposed.")

    if script_failed:
        logger.error("DB schema verification FAILED.")
        sys.exit(1)
    else:
        logger.info("DB schema verification SUCCEEDED.")
        sys.exit(0)

if __name__ == "__main__":
    # This script does not use asyncio for its main db operations for simplicity with create_engine
    # but if settings or other parts needed async, it would be different.
    # For now, we'll run main directly. If it had async parts, we'd use asyncio.run(main())
    import sys # ensure sys is imported for sys.exit()
    main() # Call directly as it's not an async def main()

# Correction: main should be async as it was defined, so use asyncio.run
# Re-add sys import as it was removed by mistake in thought process
# The main function was defined as async, so it should be called with asyncio.run
# _actual_script_will_be_corrected_in_next_block_if_this_thought_is_used_

# Corrected thought: The main function is NOT async. It uses synchronous SQLAlchemy.
# The placeholder "async def main()" was a mistake in the thought process.
# The script will be generated with "def main():"
# So, direct call to main() is fine.
# I will ensure the generated script uses `def main():` and `import sys`.Okay, the persistent `ModuleNotFoundError` is preventing the execution of Python scripts that rely on the project's internal module structure (`app.services`, `app.db`, etc.). This makes it difficult to verify the fix by using the application's own code paths.

As a robust workaround to verify the database schema directly (specifically that the `manufacturers` table now correctly handles `created_at` and `updated_at` columns as intended by the migration), I will use a script that interacts with the database using raw SQL through SQLAlchemy. This script will have minimal dependencies on the project's module structure, primarily needing only the database connection string from `config.settings`.

**Plan:**
1.  **Create a Python script** named `verify_db_timestamps.py` in the `/app` directory.
2.  **Script Content:**
    *   Import `sqlalchemy` (engine, text), `sys`, `logging`, and `settings` from `config.settings`.
    *   Use the synchronous database URL (`settings.DATABASE_URL_SYNC`).
    *   In a `main` function:
        *   Create a SQLAlchemy engine.
        *   Connect and start a session.
        *   **Insert Operation:** Execute a raw SQL statement: `INSERT INTO manufacturers (name) VALUES (:name) RETURNING id, created_at, updated_at;` with a test name.
        *   **Verification:**
            *   If the insert is successful, fetch the returned `id`, `created_at`, and `updated_at` values.
            *   Log these values.
            *   If `created_at` or `updated_at` are `None`, log an error and mark the script as failed. Otherwise, log success.
        *   **Error Handling:** Catch `sqlalchemy.exc.DBAPIError` (which includes `UndefinedColumnError`). If such an error related to the timestamp columns occurs, log it and mark failure.
        *   **Cleanup:** Delete the inserted test manufacturer using its ID.
        *   The script will `sys.exit(0)` on success and `sys.exit(1)` on failure.
3.  **Execute the script** using `python /app/verify_db_timestamps.py`. The CWD of `run_in_bash_session` is `/app`. The script will attempt to import `config.settings`. If this specific import fails, it's a much more constrained problem than the general `app.module` failures.

This approach directly tests if the database schema was altered correctly by the migration and if the default value generation for `created_at` and `updated_at` is working, which is the core of the original `UndefinedColumnError` issue.
