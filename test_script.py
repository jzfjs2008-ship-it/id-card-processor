import os
from processor import IDCardProcessor

def test_processor():
    print("Initializing Processor...")
    proc = IDCardProcessor()
    
    test_dir = "test_data"
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Mock identification for dummy test since we don't have a real face
    p_path = os.path.join(test_dir, "portrait.jpg")
    e_path = os.path.join(test_dir, "emblem.jpg")
    out_path = os.path.join(output_dir, "merged_test.jpg")
    
    print("Testing manual pair processing...")
    proc.process_pair(p_path, e_path, out_path)
    
    output_files = os.listdir(output_dir)
    if output_files:
        print(f"Success! Merged images created: {output_files}")
    else:
        print("Failed: No output images created.")

if __name__ == "__main__":
    test_processor()
