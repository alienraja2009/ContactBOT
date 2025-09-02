import sqlite3
import database

# Initialize database
database.init_db()

# Add some test messages
msg1 = database.save_message(123, "@testuser", "Test message 1")
msg2 = database.save_message(456, "@testuser2", "Test message 2")

print(f"Message IDs before reset: {msg1}, {msg2}")

# Reset IDs
success = database.reset_message_ids()
print(f"Reset success: {success}")

# Add another message to see if it starts from 1
msg3 = database.save_message(789, "@testuser3", "Test message 3")
print(f"New message ID after reset: {msg3}")

# Check if old messages still exist
conn = sqlite3.connect('messages.db')
c = conn.cursor()
c.execute("SELECT id FROM messages ORDER BY id")
rows = c.fetchall()
conn.close()
print(f"All message IDs: {[row[0] for row in rows]}")
