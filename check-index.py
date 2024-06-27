import os

def get_highest_and_least_index(basename):
    highest_index = -1  # Start with an invalid index to ensure we find a valid one
    least_index = float('inf')  # Start with an infinitely large number 
    indexes = [] 


    try:
        for entry in os.listdir(basename):
            if os.path.isfile(os.path.join(basename, entry)):
                filename = os.path.basename(entry)
                try:
                    # Extract the index number from the filename
                    index = int(os.path.splitext(filename)[0].split("-", 2)[1])
                    indexes.append(index)
                    if index > highest_index:
                        highest_index = index
                    if index < least_index:
                        least_index = index
                except (IndexError, ValueError):
                    continue

        # If no valid index was found, reset least_index to -1
        if least_index == float('inf'):
            least_index = -1

        # Save indexes to a file
        with open('downloaded_entry.txt', 'w') as f:
            for index in indexes:
                f.write(f"{index}\n")

    except FileNotFoundError:
        print(f"Directory {basename} does not exist.")
        # Return default values if directory does not exist
        highest_index = -1
        least_index = -1

    return highest_index, least_index

basename = 'dataset'
highest_index, least_index = get_highest_and_least_index(basename)
print(f"The highest index found is: {highest_index}")
print(f"The least index found is: {least_index}")

