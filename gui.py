import pygame 
import pygame.gfxdraw
import api
import sys
import math 
import threading
from tkinter.filedialog import askdirectory,asksaveasfilename,askopenfilenames

class GUI():
    def __init__(self,safe_mode=False):
        self.init_pygame()
        self.init_decoration()
        self.init_api(safe_mode)
        
    def init_pygame(self):
        # Set the dimensions of the screen
        self.screen_width = 1000
        self.screen_height = int(self.screen_width*9/16)
        # Create the screen
        self.screen = pygame.display.set_mode((self.screen_width,self.screen_height))    
        # Since running is True, the games run (stuck in loop)    
        self.running = True
        
        # Set the screen name and icon to custom ones
        pygame.display.set_caption("DataGouv Drive")
        pygame.display.set_icon(pygame.image.load("Images/icon.png"))

    def init_decoration(self):
        # Create and define colors
        
        self.colors = [(111,146,131),(105,109,125),(254,220,151),(245,227,224)]
        self.background_color = self.colors[3]
        
        # Define the fonts used 
        
        pygame.font.init()
        self.fonts = [pygame.font.Font("Nimbus.otf",35),pygame.font.Font("Nimbus.otf",55),pygame.font.Font("Nimbus.otf",25)]
        self.huge_font = pygame.font.Font("Nimbus.otf",70)
        
        #=- Elements -=#
        
        # Render texts
        self.introduction_text = self.huge_font.render("Your data.gouv drive",True,self.colors[1])
        self.loading_text = self.fonts[0].render("Loading...",True,self.colors[1])
        self.loads_texts = [[[self.fonts[1].render("Download files",True,self.colors[0]),self.fonts[1].render("Download files",True,self.colors[1])],self.fonts[1].size("Download files")[0]],
                            [[self.fonts[1].render("Upload files",True,self.colors[0]),self.fonts[1].render("Upload files",True,self.colors[1])],self.fonts[1].size("Upload files")[0]],
                            [[self.fonts[1].render("Create folder",True,self.colors[0]),self.fonts[1].render("Create folder",True,self.colors[1])],self.fonts[1].size("Create folder")[0]],]

        # Load images
        self.backs = [pygame.image.load("Images/back.png"),pygame.image.load("Images/back_hover.png")]
        self.refreshed = [pygame.image.load("Images/refresh.png"),pygame.image.load("Images/refresh_hover.png")]
        self.downloads = [pygame.image.load("Images/download.png"),pygame.image.load("Images/download_hover.png")]
        self.deletes = [pygame.image.load("Images/delete.png"),pygame.image.load("Images/delete_hover.png")]
        self.huge_loads = [pygame.image.load("Images/huge_download.png"),pygame.image.load("Images/huge_download_hover.png"),pygame.image.load("Images/huge_upload.png"),pygame.image.load("Images/huge_upload_hover.png"),pygame.image.load("Images/huge_create.png"),pygame.image.load("Images/huge_create_hover.png")]
        
        # Define buttons
        self.back_button = pygame.rect.Rect(135,self.screen_height-112,102,102)
        self.refresh_button = pygame.rect.Rect(self.screen_width-112,12,102,102)
        self.contents_buttons = [pygame.rect.Rect(180,180+i*50,620,self.fonts[0].size("e")[1]) for i in range(5)]
        self.download_buttons = [pygame.rect.Rect(810,180+i*50,50,50) for i in range(5)]
        self.delete_buttons = [pygame.rect.Rect(860,180+i*50,50,50) for i in range(5)]
        self.huge_button = pygame.rect.Rect(self.screen_width-112,self.screen_height-112,102,102)

    def init_api(self,safe):
        # Variables for the safe mode
        self.safe_usage = safe # Determine if the safe mode is enabled
        self.safe_folders = {} # Virtual folders
        self.safe_folder_id_increment = 0 # Fake folders ID
        self.safe_file_id_increment = 0 # Fake files ID
        
        # Get API-KEY and ORG-ID from the infos file
        with open("INFOS.txt","r") as f:
            infos = [line.replace("\n","") for line in f.readlines()]
        
        if not self.safe_usage: self.drive = api.Drive(*infos)
        
        # Main variables, used to now where the user is, what he is doing, what's computing
        self.directory = None # Name of the folder
        self.directory_id = 0 # Folder id
        self.scroller = 0 # Screen scrolling
        self.selected_files = [] # Files selected to download
        self.loading = False # True if the engine is computing (uploading / downloading / refreshing)
        
        # Variables for key logging
        self.listening = False 
        self.name_listened = "" # Folder name entered
        self.listening_cooldown = 0  # Oscillating "|" cooldown advancement
        self.listening_state = False # Oscillating "|" cooldown status
        self.listening_caps_lock = False # Caps lock status
        
        
        
        self.update_rendered_content()

    def get_folders(self):
        if self.safe_usage:
            return [[folder,self.safe_folders[folder]["name"]] for folder in list(self.safe_folders.keys())]
        else:
            return self.drive.available_folders
    
    def get_files(self):
        if self.safe_usage:
            return list(self.safe_folders[self.directory_id]["resources"].items())
        else:
            return self.drive.get_available_files("",self.directory_id)
    
    def get_unity(self,number):
        unity_index = int(math.log(number,10)) // 3 if number else 0
        return round(number/(10**(3*unity_index)),1) if unity_index else number,["o","ko","Mo","Go","To"][unity_index]

    def update(self):
        # Update listening cooldown if listening
        if self.listening: self.update_listening_cooldown()
        
        # Don't udpate anything else if the mouse button isn't clicked or if the api is loading something
        if not self.mouse_clicked or self.loading:
            return 
        
        # Get the amount of elements to update
        update_amount = min(5,len(self.content)-self.scroller)
        # Store the mouse position a single time
        mouse_position = pygame.mouse.get_pos()
         
        # Update everything separately
        
        self.update_content(update_amount,mouse_position)
                
        self.update_addons_content(update_amount,mouse_position)
                        
        self.update_huge_button(mouse_position)

        self.update_other_buttons(mouse_position)
        

        if not self.clicked_usefully:
            self.selected_files = []
    
    def update_rendered_content(self):
        # Reset variables
        self.scroller = 0
        self.selected_files = []
        
        #=====- ROOT -=====#
        
        if not self.directory:
            # Text displayed at the very top
            self.directory_text = self.fonts[1].render("- Directory :   Root",True,self.colors[0])
            # Content displayed in content-part of the screen
            self.content = []
            
            for i,folder in enumerate(self.get_folders()):
                # Create a render for when the file is not hovered
                usual_render = self.fonts[0].render("-   "+folder[1],True,self.colors[0]) 
                # And for when it is 
                hover_render = self.fonts[0].render("-   "+folder[1],True,self.colors[1]) 
                # And so add it to the rendered content
                self.content.append({"main":[usual_render,hover_render],
                                     "addons":[]
                                     })
            return 
        
        #=====- DIRECTORY -=====#

        # Text displayed at the very top -> the directory name
        self.directory_text = self.fonts[1].render("- Root/"+self.directory,True,self.colors[0])
        # Content displayed in content-part of the screen
        self.content = []
        
        for i,file_obj in enumerate(self.get_files()):
            # Some names can't be fully displayed, so i added restrictions and i crop them
            displayed_file_name = "-   "+self.apply_name_restriction(file_obj[1][0])                

            # Create a render for when the file is not hovered
            usual_render = self.fonts[0].render(displayed_file_name,True,self.colors[0])
            # And for when it is
            hover_render = self.fonts[0].render(displayed_file_name,True,self.colors[1])
            
            # FILE SIZE #

            # Get the size of the object in the proper unity 
            size,size_unity = self.get_unity(file_obj[1][1])
            # Define the size text displayed 
            size_text = str(size)+" "+size_unity
            # Create both the renders
            addon_usual_render = self.fonts[2].render(size_text,True,self.colors[0]) 
            addon_hover_render = self.fonts[2].render(size_text,True,self.colors[1])
            # Align the size of the file to the left, so get its size to aligne it well
            addon_text_size = self.fonts[2].size(size_text)
            addon_width = addon_text_size[0]
            addon_offset = self.fonts[0].size("e")[1] - addon_text_size[1]

            # Add everything to the rendered content
            self.content.append({"main":[usual_render,hover_render],
                                    "addons":[addon_usual_render,addon_hover_render,addon_width,addon_offset]
                                    })

    def update_listening_cooldown(self):
        # Increment the cooldown
        self.listening_cooldown += 1
        
        if self.listening_cooldown < 150:
            return

        # If the cooldown has reached its end, reset it and change state
        self.listening_cooldown = 0
        self.listening_state = not self.listening_state 
        
        # Create the new renders in function the cooldown state
        usual_render = self.fonts[0].render("-   "+(self.name_listened if self.name_listened else "Nouveau Dossier") + " |"*self.listening_state,True,self.colors[1]) 
        hover_render = self.fonts[0].render("-   "+(self.name_listened if self.name_listened else "Nouveau Dossier") + " |"*self.listening_state,True,self.colors[1]) 
        
        # Update the last content <=> the listened name
        self.content[-1] = {"rect":None,
                "main":[usual_render,hover_render],
                "addons":[]
                    }

    def update_content(self,updated_contents_amount,mouse_position):
        self.clicked_usefully = False
        
        for i in range(0,updated_contents_amount):
            # Real index of the content
            tweaked_index = self.scroller + i
            
            # Verify if the cursor is over the button
            if not self.contents_buttons[i].collidepoint(mouse_position):
                continue 
            
            # In case we're in the root -> go to the folder
            if not self.directory:
                self.directory_id, self.directory = self.get_folders()[tweaked_index]
                self.update_rendered_content()
                break 
            
            # In case we're in a folder
            
            # If the file is already selected, unselect it 
            if tweaked_index in self.selected_files:
                self.selected_files.remove(tweaked_index)
                break 
            
            # If it isn't, select it  
            self.selected_files.append(tweaked_index)
            
            self.clicked_usefully = True

    def update_addons_content(self,updated_contents_amount,mouse_position):
        if self.listening or self.selected_files:
            return 
        
        for i in range(0,updated_contents_amount):
            # Real index of the content
            tweaked_index = self.scroller + i
            
            # In case we're in a folder and the download button is pressed, send the request as a thread
            if self.directory and self.download_buttons[i].collidepoint(mouse_position):
                self.loading = True
                download_thread = threading.Thread(target=self.request_to_download,group=None,daemon=True,args=(tweaked_index,))
                download_thread.start()

            # Delete buttons
            if self.delete_buttons[i].collidepoint(mouse_position):
                if self.directory:
                    self.request_to_delete_file(tweaked_index)
                else:
                    self.request_to_delete_folder(tweaked_index)

    def update_huge_button(self,mouse_position):
        if  not self.huge_button.collidepoint(mouse_position):
            return 
        
        # If in the root -> create new folder
        if not self.directory:
            self.request_to_create_folder()
            return 

        # If in a folder
        self.loading = True
        
        # If files are selected -> download selected files
        if self.selected_files:
            download_thread = threading.Thread(target=self.request_to_multiple_download,group=None,daemon=True)
            download_thread.start()
            return 
        
        # Else -> upload some files
        upload_thread = threading.Thread(target=self.request_to_multiple_upload,group=None,daemon=True)
        upload_thread.start()

    def update_other_buttons(self,mouse_position):
        # If go back button is pressed, go back to root
        if self.directory and self.back_button.collidepoint(mouse_position): 
            self.directory = None
            self.update_rendered_content()
        
        # If refresh button is pressed -> refresh
        if self.directory and self.refresh_button.collidepoint(mouse_position):
            self.loading=True
            refresh_thread = threading.Thread(target=self.request_to_refresh,group=None,daemon=True)
            refresh_thread.start()

    def request_to_refresh(self):
        # If safe usage do nothing
        if self.safe_usage:
            self.loading = False 
            return
        
        # If real usage, ask for most recent logs
        self.drive.download_logs()
        self.loading = False 

    def request_to_download(self,index):
        # Can't download in safe mode
        if self.safe_usage:
            self.loading = False
            return 
        
        # Get the file name
        file_name = self.get_files()[index][1][0]
        # Get the extension (end of the file name)
        file_extension = file_name.split(".")[-1]
        # Get the directory where the user wants to download the file
        download_file_path = asksaveasfilename(initialfile=file_name,defaultextension=file_extension).split("/")
        # Get only the path 
        download_directory = "/".join(download_file_path[:-1])
        # Get the name entered by the user
        custom_name = download_file_path[-1]
        
        # If the user didn't finish entering the path, return nothing
        if not download_file_path[0]:
            self.loading = False
            return 
        
        # Send the request
        self.drive.download_files([file_name],self.directory,download_directory,custom_name)
        self.loading = False
    
    def request_to_multiple_download(self):
        # You can't specify the name of each file locally
        # You can if you use the single download function
        
        # Can't download in safe mode
        if self.safe_usage:
            self.loading = False
            return 
        
        # Get the files names
        files_names = [self.get_files()[index][1][0] for index in self.selected_files]

        # Get the directory
        download_directory = askdirectory()

        # No directory -> return 
        if not download_directory:
            self.loading = False
            return 
        
        # Send the request
        self.drive.download_files(files_names,self.directory,download_directory)
        self.loading = False
    
    def request_to_multiple_upload(self):
        # Get the files names
        files_names = askopenfilenames()
        
        # For safe mode 
        if self.safe_usage:
            # Create fake files that can't be downloaded (just get the files informations)
            for file_name in files_names:
                size = api.os.path.getsize(file_name)
                self.safe_folders[self.directory_id]["resources"][self.safe_file_id_increment] = [file_name.split("/")[-1],size]
                self.safe_file_id_increment += 1
        # For real usage mode
        else:
            # Send the request
            self.drive.upload_files(files_names,self.directory)
        
        # Update everything
        self.update_rendered_content()
        self.loading = False

    def request_to_delete_file(self,index):
        # Get the name of the file to delete
        file_name = self.get_files()[index][1][0]
        
        # In safe mode juste delete the fake file
        if self.safe_usage:
            del self.safe_folders[self.directory_id]["resources"][self.get_files()[index][0]]
        # In real mode send the request to the API
        else:
            self.drive.delete_files([file_name],self.directory)
            
        self.update_rendered_content()

    def request_to_delete_folder(self,index):
        # Get the name and the id of the folder to delete
        folder_id,folder_name = self.get_folders()[index]
        
        # In safe mode juste delete the fake folder
        if self.safe_usage:
            del self.safe_folders[folder_id]
        # In real mode send the request to the API
        else:
            self.drive.delete_folder(folder_name,self.directory)
            
        self.update_rendered_content()

    def request_to_create_folder(self):
        # Create temporaries folders content
        usual_render = self.fonts[0].render("-   "+"Nouveau Dossier",True,self.colors[1]) 
        hover_render = self.fonts[0].render("-   "+"Nouveau Dossier",True,self.colors[1])
        
        # Add the content
        self.content.append({"rect":None,
                            "main":[usual_render,hover_render],
                            "addons":[]
                                })

        # Enable listening mode -> wait for keys to be pressed
        self.listening = True
        
        # Scroll down to make sure the new folder is visible
        self.scroller = max(0,len(self.content)-5)

    def request_to_finish_folder(self): 
        # Set the name as default name if the name entered is empty
        self.name_listened = self.name_listened if self.name_listened else "Nouveau Dossier"
        
        # Get the folder names
        folder_names = [folder[1] for folder in self.get_folders()]
        # Get the number of folders that are almost like this one 
        occurrences = [folder_name for folder_name in folder_names if folder_name[:len(self.name_listened)] == self.name_listened]
        # If the name already is in the folders, or it exists such Name (X), change it to Name (X+1)
        if occurrences:
            self.name_listened = self.name_listened + f" ({len(occurrences)+1})"


        # In the safe mode, create a fake folder
        if self.safe_usage:
            self.safe_folders[str(self.safe_folder_id_increment)] = {"name":self.name_listened,"resources":{}}
            self.safe_folder_id_increment += 1
        # In real usage mode, send the request
        else:
            self.drive.create_new_folder(self.name_listened,"No description")
        
        # Set the variables as default
        self.listening = False
        self.name_listened = ""
        
        # Update and scroll to the new folder
        self.update_rendered_content()
        self.scroller = max(0,len(self.content)-5)

    def process_key_input(self,key):
        # Get the name of the key
        key_name = pygame.key.name(key)
        
        # Check if the key can be written
        if key_name in "abcdefghijklmnopqrstuvwxyz[0][1][2][3][4][5][6][7][8][9][0]":
            key_name = key_name.replace("[","").replace("]","")
            self.name_listened += key_name if not self.listening_caps_lock else key_name.upper()
            
        # Delete last char if the key is backspace
        if key_name == "backspace":
            self.name_listened = self.name_listened[:-1] if self.name_listened else ""
        
        # Change char case
        if key_name == "caps lock":
            self.listening_caps_lock = not self.listening_caps_lock
        
        # Add a space if expected and asked
        if key_name == "space":
            self.name_listened += " "

        # Create a new render of the thing written
        usual_render = self.fonts[0].render("-   "+(self.name_listened if self.name_listened else "Nouveau Dossier"),True,self.colors[1]) 
        hover_render = self.fonts[0].render("-   "+(self.name_listened if self.name_listened else "Nouveau Dossier"),True,self.colors[1]) 
        # Update the content
        self.content[-1] = {"rect":None,
                "main":[usual_render,hover_render],
                "addons":[]
                    }

    def apply_name_restriction(self,name): 
        return name if len(name) <= 21 else name[:21] + "..."

    def run(self): 
        while self.running:
            self.event()
            self.update()
            self.draw()

    def event(self): 
        self.mouse_clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            # MOUSE 
            if event.type == pygame.MOUSEBUTTONDOWN:
                # If a mouse button is pressed, end the listening
                if self.listening: self.request_to_finish_folder()
                # Used in update to know when mouse left button is clicked != pressed
                if event.button == 1:
                    self.mouse_clicked = True
                # Scroll UP
                if event.button == 4:
                    self.scroller = max(self.scroller-1,0)
                # Scroll DOWN
                if event.button == 5:
                    self.scroller = min(self.scroller+1,max(0,len(self.content)-5))

            # KEYBOARD
            if event.type == pygame.KEYDOWN:
                # Hotkey to go back to root
                if event.key == pygame.K_BACKSPACE and self.directory and not self.loading:
                    self.directory = None 
                    self.update_rendered_content()
                # Finish properly the listening
                elif event.key == pygame.K_RETURN:
                    if self.listening: self.request_to_finish_folder()
                # Add to listened name the key pressed if it is different from return and backspace
                elif self.listening:
                    self.process_key_input(event.key)
        
    def draw(self):
        self.screen.fill(self.background_color)
       
        self.draw_scroll_bar()
        self.draw_fixed_elements()
        self.drawContent()

        pygame.display.flip()

    def draw_scroll_bar(self):
        # If there is no content to display, don't draw a scroll bar
        if not self.content:
            return 
        
        # Get the amount of divisions of the scroll bar
        divisions = max(0,len(self.content)-5) + 1
        
        # Get the height of the scroll bar
        height = max(5,int(240 / divisions))
        # Get the y coordinate
        y = int((240 / divisions)*self.scroller + 180)
        
        # Draw the scroll bar
        pygame.gfxdraw.aapolygon(self.screen,[[910,y],[910,y+height],[915,y+height],[915,y]],self.colors[0])
        pygame.gfxdraw.filled_polygon(self.screen,[[910,y],[910,y+height],[915,y+height],[915,y]],self.colors[0])
           
    def draw_fixed_elements(self):
        # Draw huge rects all around
        
        # Very left one
        pygame.gfxdraw.aapolygon(self.screen,[[0,0],[0,self.screen_height],[80,self.screen_height],[80,0]],self.colors[1])
        pygame.gfxdraw.filled_polygon(self.screen,[[0,0],[0,self.screen_height],[80,self.screen_height],[80,0]],self.colors[1])
        # Small one
        pygame.gfxdraw.aapolygon(self.screen,[[120,self.screen_height],[128,self.screen_height],[128,185],[120,185]],self.colors[0])
        pygame.gfxdraw.filled_polygon(self.screen,[[120,self.screen_height],[128,self.screen_height],[128,185],[120,185]],self.colors[0])
        
        # Draw the different texts from top to bottom

        self.screen.blit(self.introduction_text,(100,20))
        
        self.screen.blit(self.directory_text,(120,100))

        if self.loading: 
            self.screen.blit(self.loading_text,(145,self.screen_height-65))
        
    def drawContent(self):
        # Get the mouse position a single time
        mouse_pos = pygame.mouse.get_pos()

        # Get the amount of element to draw, max is 5, minimum is the amount of contents if it is inferior to 5
        drawn_contents = min(5,len(self.content)-self.scroller)
        
        # Draw each content
        for i in range(0,drawn_contents):
            # Because of scrolling, the displayed inde isn't the true index
            tweaked_index = i+self.scroller
            
            # Get if the content text is hovered
            hovered = self.contents_buttons[i].collidepoint(mouse_pos) or tweaked_index in self.selected_files
            
            # Draw the content main text
            self.screen.blit(self.content[tweaked_index]["main"][hovered],(180,180+i*50))

            # If the content has addons like file size, draw it 
            if self.content[tweaked_index]["addons"]:
                self.screen.blit(self.content[tweaked_index]["addons"][hovered],(800-self.content[tweaked_index]["addons"][2],180+i*50+self.content[tweaked_index]["addons"][3]))
            
            # Draw the buttons too
            
            # Draw the delete button
            self.screen.blit(self.deletes[self.delete_buttons[i].collidepoint(mouse_pos) or tweaked_index in self.selected_files],(870,190+i*50))

            if not self.directory:
                continue
            
            # Draw the download button only for files, not for folder
            self.screen.blit(self.downloads[self.download_buttons[i].collidepoint(mouse_pos) or tweaked_index in self.selected_files],(820,190+i*50))
            

        # Bottom right button -> upload, download, create
        self.screen.blit(self.huge_loads[self.huge_button.collidepoint(mouse_pos)+2*(not self.selected_files)+2*(not self.directory)],(self.screen_width-102,self.screen_height-102))
        self.screen.blit(self.loads_texts[(not self.selected_files )+ (not self.directory)][0][self.huge_button.collidepoint(mouse_pos)],((self.screen_width-122-self.loads_texts[(not self.selected_files) + (not self.directory)][1],self.screen_height-82)))

        # If the directory isn't the root and the api isn't loading, draw the refresh button and the go back button
        if not self.loading and self.directory:
            self.screen.blit(self.backs[self.back_button.collidepoint(mouse_pos)],(145,self.screen_height-102))
            self.screen.blit(self.refreshed[self.refresh_button.collidepoint(mouse_pos)],(self.screen_width-102,22))

instance = GUI(sys.argv[1] if len(sys.argv)>1 else False)
instance.run()