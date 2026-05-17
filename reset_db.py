import psycopg2
import psycopg2.extensions
import subprocess
from decouple import config

# Database credentials from .env
DB_NAME = config("DB_NAME", default="saas_billing_db")
DB_USER = config("DB_USER", default="postgres")
DB_PASSWORD = config("DB_PASSWORD", default="postgres")
DB_HOST = config("DB_HOST", default="localhost")
DB_PORT = config("DB_PORT", default="5432")

def reset_database():
    print(f"Connecting to postgres to drop and recreate {DB_NAME}...")
    try:
        # Connect to the default 'postgres' database to drop/create our target db
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Terminate existing connections
        print("Terminating existing connections...")
        cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{DB_NAME}'
              AND pid <> pg_backend_pid();
        """)
        
        # Drop database
        print(f"Dropping database {DB_NAME}...")
        cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME};")
        
        # Create database
        print(f"Creating database {DB_NAME}...")
        cursor.execute(f"CREATE DATABASE {DB_NAME};")
        
        cursor.close()
        conn.close()
        print("Database reset successful.")
        
    except Exception as e:
        print(f"Error resetting database: {e}")
        return False
        
    return True

def run_command(command, description):
    print(f"\n--- {description} ---")
    print(f"Running: {command}")
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        return False
    return True

if __name__ == "__main__":
    print("WARNING: This will delete everything in your database and reset it from scratch!")
    confirm = input("Are you sure you want to proceed? (yes/no): ")
    if confirm.lower() not in ['yes', 'y']:
        print("Aborted.")
        exit(0)
        
    if reset_database():
        python_exe = r".\venv\Scripts\python.exe"
        
        # Clear old migrations in tenants app to reflect our new models
        import os, glob
        migrations_dir = os.path.join("tenants", "migrations")
        if os.path.exists(migrations_dir):
            for file in glob.glob(os.path.join(migrations_dir, "*.py")):
                if not file.endswith("__init__.py"):
                    try:
                        os.remove(file)
                        print(f"Deleted old migration: {file}")
                    except OSError:
                        pass
                        
        commands = [
            (f"{python_exe} manage.py makemigrations", "Making new migrations"),
            (f"{python_exe} manage.py migrate_schemas --shared", "Applying shared schema migrations"),
            (f"{python_exe} manage.py seed_integrations", "Seeding integrations"),
            (f"{python_exe} manage.py seed_subscription_types", "Seeding subscription types"),
            (f"{python_exe} manage.py createsuperuser", "Creating superuser")
        ]
        
        for cmd, desc in commands:
            success = run_command(cmd, desc)
            if not success:
                print("Stopping setup due to error.")
                break
                
        print("\n=== Setup Complete ===")
        print("You can now restart your dev server with: .\\venv\\Scripts\\python.exe manage.py runserver")
