import re
import string
import random
import sys
import os

conf_number = 0
def replace_tags(input_text, conf_name):
    global conf_number
    currentTag = re.search("#\d+{", input_text)
    if currentTag:
        TagRegex = currentTag.group() + "[^}]+}[^#]*#"
        for i in range(len(re.search(TagRegex, input_text).group().split('}')[0].split(','))):
            newInput = input_text
            tagName = ""
            for similarTag in re.findall(TagRegex, input_text):
                similarTagList = similarTag.split('{')[1].split('}')[0].split(',')
                newInput = re.sub(TagRegex, similarTagList[i], newInput, 1)
                tagName += ("#" + re.search("(?<=})[^#]*(?=#)", similarTag).group() + ":" + str(similarTagList[i]))
            replace_tags(newInput, conf_name + tagName)
    else:
        conf_number += 1
        replace_vars(input_text, "{:04}".format(conf_number) + conf_name)

def replace_vars(input_text, conf_name):
    currentVar = re.search("\?\d+L\d+[sd]", input_text)
    if currentVar:
        if currentVar.group()[-1] == 's':
            replace_vars(input_text.replace(currentVar.group(),str(''.join(random.choices(string.ascii_uppercase + string.digits,k=int(currentVar.group().split('L')[1].split('s')[0]))))),conf_name)
        else:
            replace_vars(input_text.replace(currentVar.group(),str(''.join(random.choices(string.digits,k=int(currentVar.group().split('L')[1].split('d')[0]))))),conf_name)
    else:
        with open(os.path.join(output_directory, f"{conf_name}#.xml"), 'w') as outfile:
            outfile.write(input_text)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py input_file,output_directory")
        sys.exit(1)

    input_file_path, output_directory = sys.argv[1].split(',')

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    with open(input_file_path, 'r') as inputFile:
        input_text = inputFile.read()
    replace_tags(input_text, "")
