import requests 
import json
import os 


class Drive():
    def __init__(self,api_key,org_id):
        self.API = 'https://www.data.gouv.fr/api/1'
        self.API_KEY = api_key #"eyJhbGciOiJIUzUxMiJ9.eyJ1c2VyIjoiNjYxZDA4OTNjYWQ4MTA4NTMzNmVhOGM1IiwidGltZSI6MTcxMzE3ODk2MS4zMTA4OTk3fQ.0nG_M_8kNGjfmPxOQNK1oz8-cgvXoC0DihofZ3neEGogX658xdfvyHhbM473JVqOU_r_6Nh2PPCwZ8DPVp8WJA"
        self.ORG = org_id #'661d09086834682251155896'
 
        self.HEADERS = {
            'X-API-KEY': self.API_KEY,
        }
        
        self.logs_dataset_id = ""
        self.logs_resource_id = False
        
        self.available_folders = []

        self.get_logger()
        self.get_available_folders()

    #== LOGS RELATED METHODS ==#

    def create_logger(self):
        # Create a logs dataset 

        url = self.api_url('/datasets/')
        logs_response = requests.post(url, json={
            'title': 'Logs',
            'description': 'Logs of the drive, store folders informations.',
            'organization': self.ORG,
            'private':True
        }, headers=self.HEADERS)

        self.logs_dataset_id = json.loads(logs_response.text)["id"]

        # Create a log file

        blank_logs = {"folders":{}}
        self.logs = blank_logs
        self.upload_logs()
    
    def get_logger(self):
        #= Check if there is a logs dataset in the organization  =#  
        #= If there is : get the ids =#
        #= If there isn't create a new one =# 

        # Get organization datasets
        url = self.api_url(f"/organizations/{self.ORG}/datasets/")
        organization_datasets  = requests.get(url,headers=self.HEADERS)

        # Sort
        logger_dataset = [dataset for dataset in json.loads(organization_datasets.text)["data"] if ["Logs",None] == [dataset["title"],dataset["deleted"]]]
        
        # In case no logs dataset has been found -> create the dataset
        if not logger_dataset:
            
            self.create_logger()
            return 

        # Get the first element as the logs dataset
        logger_dataset = logger_dataset[0]
        
        # Get the logs dataset ID
        self.logs_dataset_id = logger_dataset["id"]

        # Get the logs file ID        
        logger_resource = [resource for resource in logger_dataset["resources"] if resource["title"]=="logs.json"][0]
        self.logs_resource_id = logger_resource["id"]
        
    def download_logs(self):
        # Get the right url
        url = self.api_url(f"/datasets/r/{self.logs_resource_id}")
        # Send the request
        response = requests.get(url,allow_redirects=True)
        
        self.logs = json.loads(response.content)
        
    def upload_logs(self):
        # Create a temporary file for the logs
        with open('Temp/logs.json', 'w') as f:
            json.dump(self.logs, f)

        # Upload the log file
        self.logs_resource_id = self.upload('Temp/logs.json',self.logs_dataset_id,self.logs_resource_id)["id"]
        
        # Delete the temporary file
        os.remove('Temp/logs.json')
    
    def reset_logs(self):
        self.logs = {"folders":{}}
        self.upload_logs()

    #== FOLDERS RELATED METHODS ==#

    def create_new_folder(self,folder_name,folder_description=""):
        # Create the dataset

        url = self.api_url('/datasets/')
        folder_creation_response = requests.post(url, json={
            'title': folder_name,
            'description': folder_description,
            'organization': self.ORG,
            'private':True
        }, headers=self.HEADERS)
        
        folder_id = json.loads(folder_creation_response.text)["id"]
        
        # Update the logs 
        
        self.logs["folders"][folder_id] = {"name":folder_name,"resources":{}}
        self.upload_logs() 
        
        # Update logs and available folders
        self.get_available_folders()

    def delete_folder(self,folder_name):
        # Get the corresponding id of the name
        folder_id = [folder[0] for folder in self.get_available_folders() if folder[1] == folder_name]

        # If no id is found, raise an error
        if not folder_id:
            assert "folder doesn't exist"        

        # Get the right id (list -> string)
        folder_id = folder_id[0]
        
        # Send the request to delete the dataset
        url = self.api_url('/datasets/{}/'.format(folder_id))
        delete_response = requests.delete(url, headers=self.HEADERS)
        
        # Remove the dataset from the logs
        del self.logs["folders"][folder_id]
        
        # Update the whole thing
        self.upload_logs()
        self.get_available_folders()

    def get_available_folders(self):
        # Make sure to have the most recent logs
        self.download_logs()
        # Get the folders in the logs -> keep the name and the id
        self.available_folders = [(folder_id,self.logs["folders"][folder_id]["name"]) for folder_id in list(self.logs["folders"].keys())]
        return self.available_folders

    def delete_all_folders(self):
        for folder in self.get_available_folders():
            self.delete_folder(folder[1])

    #== RESOURCES RELATED METHODS ==#
    
    def upload_files(self,files,folder_name):
        # Get the id of the selected folder
        folder_id = [folder[0] for folder in self.get_available_folders() if folder[1]==folder_name][0]
        
        # For each file, upload it, and update the logs
        for u_file in files:
            u_file_data = self.upload(u_file,folder_id)
            self.logs["folders"][folder_id]["resources"][u_file_data["id"]] = [u_file.split("/")[-1],u_file_data["filesize"]]

        # Update the whole logs at once
        self.upload_logs()
        self.download_logs()

    def download_files(self,files,folder_name,path="Download",custom_name=""):
        self.download_logs()
        
        # Get the id of the selected folder
        folder_id = [folder[0] for folder in self.get_available_folders() if folder[1]==folder_name][0]
        folder_resources = self.logs["folders"][folder_id]["resources"]    

        

        for u_file in files:
            file_id = [file_key  for file_key in list(folder_resources.keys()) if folder_resources[file_key][0]==u_file]
            
            # File not found, raise an error
            if not file_id:
                continue
            
            file_id = file_id[0]
            
            download_path = f'{path}/{custom_name if custom_name else u_file}'

            # Get the right url
            url = self.api_url(f"/datasets/r/{file_id}")
            # Send the request
            download_response = requests.get(url,allow_redirects=True,headers=self.HEADERS)
            # Save the logs in a temporary file 
            open(download_path, 'wb').write(download_response.content)

    def delete_files(self,files,folder_name):
        self.download_logs()
        
        # Get the id of the selected folder
        folder_id = [folder[0] for folder in self.get_available_folders() if folder[1]==folder_name][0]
        folder_resources = self.logs["folders"][folder_id]["resources"]    

        for u_file in files:
            file_id = [file_key  for file_key in list(folder_resources.keys()) if folder_resources[file_key][0]==u_file]
            
            # File not found, raise an error
            if not file_id:
                print("no file found")
                continue
            
            file_id = file_id[0]

            # Get the right url
            url = self.api_url(f"/datasets/{folder_id}/resources/{file_id}/")
            # Send the request
            delete_response = requests.delete(url,headers=self.HEADERS)
            
            # Remove the file from the logs
            del self.logs["folders"][folder_id]["resources"][file_id]
            
        # Update the whole logs at once
        self.upload_logs()
        self.download_logs()
    
    def get_available_files(self,folder_name,folder_id=0):
        if not folder_id:
            folder_id = [folder[0] for folder in self.get_available_folders() if folder[1]==folder_name][0]
            
        folder_resources = self.logs["folders"][folder_id]["resources"]    
    
        return list(folder_resources.items())

    #== OTHER METHODS ==#

    def api_url(self,path):
        return self.API+path

    def upload(self,file_name,dataset,resource=False):
        # Change extension in case the extension isn't allowed by data.gouv
        
        if file_name.split(".")[1] not in ("json","txt","csv"):
            modified_file_name = file_name.split(".")[0]+".txt"
        else:
            modified_file_name = file_name
            
        os.rename(file_name,modified_file_name)
        
        # Case disjunction : either the file already exists, either it doesn't --> differents requests

        if not resource:
            url = self.api_url('/datasets/{}/upload/'.format(dataset))
        else:
            url = self.api_url('/datasets/{}/resources/{}/upload/'.format(dataset, resource))

        # Send the request to upload the file 

        response = requests.post(url, files={
            'file': open(modified_file_name, 'rb')
        }, headers=self.HEADERS)
        
        new_resource_data = json.loads(response.text)
        
        new_resource_id = new_resource_data["id"]
        
        url = self.api_url('/datasets/{}/resources/{}/'.format(dataset, new_resource_id))
        response = requests.put(url, json={
            'title': file_name.split("/")[-1],
        }, headers=self.HEADERS)
        
        # Get back the file to its original name
        os.rename(modified_file_name,file_name)
        
        # Return the ID of the file
        return new_resource_data

# EXAMPLES

#driver.create_new_folder("Dossier Démonstration","Un dossier pour montrer comment ça marche")
#driver.upload_files(["main.py","INFOS.txt"],"Dossier Démonstration")
#driver.create_new_folder("Autre Dossier","Un autre dossier pour montrer comment ça marche")
#driver.download_files(["main.py","gui.py"],"Dossier Démonstration")
#driver.delete_files(["INFOS.txt"],"Dossier Démonstration")

