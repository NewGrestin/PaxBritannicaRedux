###A Python code by Arj that will turn national focus code ids into loc entries, assuming that your focus names are formatted like TAG_focus_name_in_hyphenated_form

import sys
#myFile = open(r"C:\Users\17138\Documents\Paradox Interactive\Hearts of Iron IV\mod\dbkgithub\common\national_focus\ITA_socialist_paths.txt") ##file path

myFile = open(r"C:\Users\Arj\Documents\Paradox Interactive\Hearts of Iron IV\mod\PaxBritannicaGithub\common\national_focus\PB_Germany.txt") ##file path
substring = "id ="
substring2 = "relative"
substring3 = "PB_GER_" ##put your country tag here

for line in myFile:
    if(substring in line):
        values = line.split("id = ")
        if(substring2 not in values[0]):
            if(substring3 in values[1]):
                nohypenate = values[1].split("_")
                print(values[1].strip('\n') + ":0", end=" ", flush=True)
                print('"', end="", flush=True)
                for nohypen in range (1, len(nohypenate)):
                    print(nohypenate[nohypen].capitalize().strip('\n') + '"' if nohypen==len(nohypenate)-1 else nohypenate[nohypen].capitalize(), end=" ", flush=True)
                print("")
                print(values[1].strip('\n') + "_desc:0" + ' ""')