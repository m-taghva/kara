import json
import os
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
from alive_progress import alive_bar
from PIL import Image

# Convert UTC times to Tehran time
def convert_to_tehran_time(utc_time):
    utc_time = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = pytz.timezone('UTC').localize(utc_time)
    tehran_time = utc_time.astimezone(pytz.timezone('Asia/Tehran'))
    return tehran_time

def dashboard_maker(directory, output_path):
    # Gather all image file paths from the directory
    image_paths = [
        os.path.join(directory, file) for file in os.listdir(directory)
        if file.endswith(('.png')) and '-dashboard' not in file
    ]
    if not image_paths:
        print("No images found to combine.")
        return
    # Open images and calculate the size for the combined image
    images = [Image.open(image_path) for image_path in image_paths]
    # Determine the number of images per row and rows needed
    images_per_row = 2
    rows = (len(images) + images_per_row - 1) // images_per_row
    # Calculate the width and height of the combined image
    max_width = max(image.width for image in images)
    max_height = max(image.height for image in images)
    combined_width = max_width * images_per_row
    combined_height = max_height * rows
    # Create a new blank image to hold the combined output
    combined_image = Image.new('RGB', (combined_width, combined_height))
    # Paste images into the combined image
    for index, image in enumerate(images):
        x_offset = (index % images_per_row) * max_width
        y_offset = (index // images_per_row) * max_height
        combined_image.paste(image, (x_offset, y_offset))
    # Save the combined image
    combined_image.save(output_path)
    print(f"image append to {os.path.basename(output_path)}")

def image_maker(query_output, server_name, parent_dir):
    data = json.loads(query_output)
    # Create a directory for the server's images if it doesn't exist
    server_dir = os.path.join(parent_dir, "query_results", f"{server_name}-images")
    if not os.path.exists(server_dir):
        os.makedirs(server_dir)
    image_paths = []
    with alive_bar(title=f"Generating Image for {server_name}") as bar:
        # Extract data and create graphs for each time range
        for entry in data["results"]:
            for series in entry["series"]:
                metric_name = series["name"]
                value_column = series["columns"][1]  
                values = series["values"]
                # Extract time and value data
                times_utc = [convert_to_tehran_time(value[0]) for value in values]
                values = [value[1] for value in values]
                # Calculate min, max, and average values
                min_value = min(values)
                max_value = max(values)
                avg_value = sum(values) / len(values)
                # Get corresponding times for min, max, and average
                min_time = times_utc[values.index(min_value)]
                max_time = times_utc[values.index(max_value)]
                avg_time = times_utc[len(values) // 2]  # Approximation for average value
                plt.figure(figsize=(10, 6))
                plt.plot(times_utc, values, marker='.', linestyle='-', linewidth=1, color='black', label='Values')
                # Highlight min, max, and avg with different colors
                plt.plot(min_time, min_value, 'ro', label=f'Min: {min_value}')
                plt.plot(max_time, max_value, 'go', label=f'Max: {max_value}')
                plt.plot(avg_time, avg_value, 'bo', label=f'Avg: {avg_value:.2f}')
                plt.xlabel("Time (Asia/Tehran)")
                plt.ylabel("Value")
                plt.title(f"{metric_name} ({value_column.capitalize()}) - Server: {server_name}")
                plt.xticks(rotation=90)
                plt.legend()
                # Show x-axis labels every 1 minute
                time_range_start = times_utc[0]
                time_range_end = times_utc[-1]
                time_interval = timedelta(minutes=1)
                x_ticks = []
                x_labels = []
                current_time = time_range_start
                while current_time < time_range_end:
                    x_ticks.append(current_time)
                    x_labels.append(current_time.strftime("%Y-%m-%d %H:%M:%S"))
                    current_time += time_interval 
                # Ensure the last time is included in the x-axis
                x_ticks.append(time_range_end)
                x_labels.append(time_range_end.strftime("%Y-%m-%d %H:%M:%S"))
                plt.xticks(x_ticks, x_labels)
                plt.grid(True)
                plt.tight_layout()
                output_filename = f"{server_name}-{metric_name.replace('.', '-')}-{value_column}_{time_range_start.strftime('%Y-%m-%d-%H-%M-%S')}-{time_range_end.strftime('%Y-%m-%d-%H-%M-%S')}.png"
                output_filepath = os.path.join(server_dir, output_filename)
                plt.savefig(output_filepath, dpi=300)
                plt.close()
                print(f"\033[1;33m{output_filename}\033[0m saved")
                image_paths.append(output_filepath)
                bar()
    dashboard_maker(server_dir, os.path.join(server_dir, f"{server_name}-dashboard.png"))
