
import glob
import os

path = r"gfx\interface\goals"

os.chdir(path)
print(os.listdir())
files = glob.glob("*.dds")
print(files)

files.sort(key=os.path.getmtime)

for filename in files:
   filenamestorage = filename[:-4]
   if filename.endswith(".dds"):
    print("spriteType = {")
    print(" " + "name =" + '"' + "GFX_goal_" + filenamestorage + '"') 
    print(" " + "texturefile = " + '"' + "gfx/interface/goals/" + filename + '"')
    print("}")
    print("")
   else:
       continue

    
