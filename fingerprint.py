from fingerprint_sdk import Scanner  # This would be the actual SDK import

def enroll_fingerprint(student_id):
    scanner = Scanner()
    try:
        scanner.initialize()
        fingerprint_data = scanner.capture(enrollment=True)
        save_to_database(student_id, fingerprint_data)
        return True
    except ScannerError as e:
        print(f"Error: {e}")
        return False
    finally:
        scanner.close()
