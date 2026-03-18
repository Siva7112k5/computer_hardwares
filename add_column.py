# add_column.py
from app import app, db

with app.app_context():
    try:
        db.engine.execute('ALTER TABLE "order" ADD COLUMN email VARCHAR(120)')
        print("✅ Email column added successfully to order table")
    except Exception as e:
        print(f"❌ Error: {e}")