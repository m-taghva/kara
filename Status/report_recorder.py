import subprocess
import argparse

def read_template_file(template_file_path):
    with open(template_file_path, 'r') as template_file:
        return template_file.read()

def create_html_template(template_content, paragraphs):
    # Join paragraphs with <p> tags
    body_content = "\n".join([f"<p>{paragraph}</p>" for paragraph in paragraphs])

    # Replace placeholders in the template with actual content
    template = template_content.replace("{body_content}", body_content)
    return template

def save_html_file(file_path, content):
    with open(file_path, 'w') as file:
        file.write(content)

def main():
    parser = argparse.ArgumentParser(description="Generate HTML report from a text file.")
    parser.add_argument("-ic", "--input_config", required=True, help="Input text file path.")
    parser.add_argument("-it", "--input_template", required=True, help="Template HTML file path.")
    parser.add_argument("-oh", "--html_output", required=True, help="Output HTML file path.")
    parser.add_argument("-kt", "--page_title", required=True, help="Kateb page title.")
    args = parser.parse_args()
    
    input_config_file = args.input_config
    input_template_file = args.input_template
    html_output = args.html_output
    page_title = args.page_title

    # Read content from the input text file
    with open(input_config_file, 'r') as txt_file:
        paragraphs = [line.strip() for line in txt_file.readlines()]

    # Read the HTML template from the user-specified file
    template_content = read_template_file(input_template_file)

    # Create HTML template
    html_content = create_html_template(template_content, paragraphs)

    # Save HTML file
    save_html_file(html_output, html_content)
    print(f"HTML template saved to: {html_output}")

    # Assuming that pwb.py is a Python script, you can run it directly without using subprocess
    pybot = f"python3 pwb.py ./scripts/userscripts/page-maker-html2.7.py -H {html_output} -T {page_title}"
    subprocess.call(pybot, shell=True)

if __name__ == "__main__":
    main()
