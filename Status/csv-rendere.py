import pandas as pd
from PIL import Image, ImageDraw, ImageFont

def csv_to_image(csv_file, output_image):
    # Read CSV file into a DataFrame
    df = pd.read_csv(csv_file)
    # Convert DataFrame to an image
    image = create_image_from_dataframe(df)
    # Save the image
    image.save(output_image)

def create_image_from_dataframe(df):
    # Get the dimensions of the DataFrame
    num_rows, num_cols = df.shape

    # Set image properties
    cell_width = 120
    cell_height = 20
    font_size = 15

    # Create a blank image
    image_width = num_cols * cell_width
    image_height = (num_rows + 1) * cell_height  # +1 for header row
    image = Image.new('RGB', (image_width, image_height), 'white')
    draw = ImageDraw.Draw(image)
    # Use the default font that comes with Pillow
    font = ImageFont.load_default()
    # Draw the header row
    for col, column_name in enumerate(df.columns):
        draw.rectangle([col * cell_width, 0, (col + 1) * cell_width, cell_height], outline='black', fill='lightgray')
        draw.text((col * cell_width + 5, 5), str(column_name), font=font, fill='black')
    # Draw the data rows
    for row in range(num_rows):
        for col, value in enumerate(df.iloc[row]):
            draw.rectangle([col * cell_width, (row + 1) * cell_height, (col + 1) * cell_width, (row + 2) * cell_height],
                           outline='black', fill='white')
            draw.text((col * cell_width + 5, (row + 1) * cell_height + 5), str(value), font=font, fill='black')
    return image

if __name__ == "__main__":
    # Replace 'input.csv' with your CSV file and 'output.png' with the desired image file name
    csv_to_image('./out/query_results/2023-07-31-09:30:00_2023-07-31-10:00:00.csv', 'myout.png')
