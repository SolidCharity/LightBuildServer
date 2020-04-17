from subprocess import Popen, PIPE, STDOUT
import sys

command="./test.sh"
child = Popen(command, stdout=PIPE, stderr=STDOUT, encoding="utf-8", universal_newlines=True, shell=True)
processFinished = False
returncode=None

while True:
   try:
        line=child.stdout.readline()
        print(line)
   except UnicodeDecodeError as e:
        line="UnicodeDecodeError Problem with decoding the log line"

   if (len(line) == 0) and processFinished:
        break;


   try:
      with open("test.log", 'ab') as f:
        f.write(line.encode("utf-8"))
   except:
      print ("Unexpected error:", sys.exc_info())
   sys.stdout.flush()



   returncode = child.poll()
   if not processFinished and returncode is not None:
        processFinished = True

print("finish")
