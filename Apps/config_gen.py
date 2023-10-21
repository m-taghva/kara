import re
filename = 0
def replace_tags(input_text):
    global filename
    currentTag = re.search("#\d*{", input_text)
    if currentTag:
        TagReg = currentTag.group() + "[^}]*}"
        irep = re.search(TagReg, input_text).group().split(',')
        for i in range(len(irep)):
            newFile = input_text
            for j in re.findall(currentTag.group(), input_text):
                rep = re.search(TagReg, newFile)
                rep = re.search("{.*}", rep.group())
                repList = rep.group().split('{')[1].split('}')[0].split(',')
                newFile = re.sub(TagReg, repList[i], newFile, 1)
            replace_tags(newFile)
    else:
        filename += 1
        with open(f"./workloads/{filename}.xml", 'w') as outfile:
            outfile.write(input_text)

# Read the input file
with open('input', 'r') as infile:
    input_text = infile.read()
replace_tags(input_text)
