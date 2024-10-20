‪<h2>Kara</h2>
<h3>open stack swift performance and monitoring tools</h3>
<img src="kara_chart.gif" width="800" height="500"/>
    <img src="kara_tools.gif" width="800" height="500"/>
  
    ## Attention ! after clone repository, please remove (.placeholder) files inside ./results/ ##
    installing kara:
      Step 1: Installing CosBench First, you need to install the CosBench tool. For familiarization and installation guidance, you can refer to the document Cloud_Object_Storage_Benchmark_(COSBench).
            After installation, go to the main directory and make the cli.sh script executable with the following commands, and create a soft link in the /usr/bin path:
                sudo chmod +x /home/user/cosbench/0.4.2.c4/cli.sh
                sudo ln -s /home/user/cosbench/0.4.2.c4/cli.sh /usr/bin/cosbench
      
      Step 2: Cloning the latest version of the program from OpenGit
            git clone https://opengit.ir/smartlab/kara
            
      Step 3: Operating system settings Create a dedicated user for Kara in mc and all servers of Hyola, or in specific cases, use existing users with sudo access:
            adduser kara
            Edit the sudoers file and grant permission to the user running Kara on the host server and Hyola servers to execute sudo commands without a password:
                # visudo
                %sudo ALL=(ALL:ALL) ALL
                kara ALL=(ALL) NOPASSWD: ALL
   
    Step 4: Running the configure tool After completing the previous steps, go to the manager directory and run the configure program to execute some prerequisite processes and install Kara:
            bash configure.sh
            
        Step 4-1: Installing prerequisite libraries
                Note: Only if the configure tool fails to install them, proceed with installing these on the Kara server:
                apt install -y python pip
                pip install pytz datetime matplotlib pandas alive_progress BeautifulSoup4 wikitextparser mwparserfromhell sshpass

    
