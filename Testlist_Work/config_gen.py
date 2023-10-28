import re
import string
import random

filename = 0
def replace_tags(input_text,wname):
    global filename
    currentTag = re.search("#\d+{", input_text)
    if currentTag:
        TagReg = currentTag.group() + "[^}]+}[^#]*#"
        irep = re.search(TagReg, input_text).group().split('}')[0].split(',')
        for i in range(len(irep)):
            newFile = input_text
            tname=""
            for j in re.findall(currentTag.group(), input_text):
                rep = re.search(TagReg, newFile)
                repList = rep.group().split('{')[1].split('}')[0].split(',')
                newFile = re.sub(TagReg, repList[i], newFile, 1)
                tname += ("#" + re.search("}[^#]*#", rep.group()).group().split('}')[1].split('#')[0] +":"+ str(repList[i]))
            replace_tags(newFile,wname+tname)
    else:
        filename += 1
        currenctVar = re.search("\?\d+L\d+[sd]", input_text)
        replace_vars(input_text,"{:04}".format(filename)+wname)

def replace_vars(input_text,wname):
    currenctVar = re.search("\?\d+L\d+[sd]", input_text)
    if currenctVar:
        if currenctVar.group()[-1]=='s':
            replace_vars(input_text.replace(currenctVar.group(), str(''.join(random.choices(string.ascii_uppercase + string.digits, k=int(currenctVar.group().split('L')[1].split('s')[0]))))),wname)
        else:
            replace_vars(input_text.replace(currenctVar.group(), str(''.join(random.choices(string.digits, k=int(currenctVar.group().split('L')[1].split('d')[0]))))),wname)
    else:
        with open(f"./workloads/{wname}#.xml", 'w') as outfile:
            outfile.write(input_text)

# Read the input file
with open('input', 'r') as infile:
    input_text = infile.read()
replace_tags(input_text,"")
