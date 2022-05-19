
import glob
import os

path = r"history/countries"

os.chdir(path)
print(os.listdir())
files = glob.glob("*.txt")
print(files)

files.sort(key=os.path.getmtime)


i = 0

for filename in files:
   if "set_technology" not in open(filename, encoding="utf8").read():
    openedfile = open(filename, "a", encoding="utf8")
    openedfile.write("set_technology = {\n")
    openedfile.write(" " + "infantry_weapons1930 = 1\n")
    openedfile.write(" " + "tech_support = 1\n")
    openedfile.write(" " + "early_fighter = 1\n")
    openedfile.write(" " + "basic_train = 1\n")
    openedfile.write("}")

    i = i + 1
   else:
       continue

    
