Step 1: Set Variables
---------------------

The instructions below assume that you are in the project's root directory.

Typically it will be necessary to first login to Azure. Select the 'dev' account.
```powershell
az login --scope https://management.core.windows.net//.default
```

Then proceed to set the necessary environment variables:
```powershell
$resourceGroup = "eeca-rg-DWBI-dev-aue"
$acrName = "eecaacrdwbidevaue"
$location = "australiaeast"
$appServicePlan = "home-efficiency-plan"
$webAppName = "home-efficiency-calculator-app"
$image = "home-efficiency-calculator:1.1.0"
$loginServer = az acr show -n $acrName --query loginServer --output tsv
$imageTag = "$loginServer/$image"
$acrPassword = az acr credential show -n $acrName --query "passwords[0].value" -o tsv
$extraCAcert = "/path/to/ZscalerRootCertificate-2048-SHA256-Feb2025.crt"
```

Step 2: Ensure the Docker image is built and pushed to the Azure Container Registry
---------------------

```powershell
docker login -u $acrName -p $acrPassword $loginServer
# If not running from behind ZScaler, no need to pass the
# EXTRA_CA_CERT build argument in the following command:
docker build --build-arg EXTRA_CA_CERT=$extraCAcert -t $image .
docker tag $image $imageTag
docker push $imageTag
```

Step 3: Create an App Service Plan for Linux containers
-------------------------------------------------------

```powershell
az appservice plan create `
  --name $appServicePlan `
  --resource-group $resourceGroup `
  --location $location `
  --is-linux `
  --sku B1  # Basic plan (supports custom containers)
```

Step 4: Create the Web App
--------------------------------------------

```powershell
az webapp create `
  --resource-group $resourceGroup `
  --plan $appServicePlan `
  --name $webAppName `
  --deployment-container-image-name $imageTag
```

Step 5: Configure the container with ACR credentials
-----------------------------------------------------

```powershell
az webapp config container set `
  --name $webAppName `
  --resource-group $resourceGroup `
  --container-image-name $imageTag `
  --container-registry-url https://$loginServer `
  --container-registry-user $acrName `
  --container-registry-password $acrPassword
```

Step 6: Restart the app and tell Azure explicitly to run Uvicorn on port 80
----------------------------------------------------------------------------

```powershell
az webapp config set `
  --resource-group $resourceGroup `
  --name $webAppName `
  --startup-file "uvicorn app.main:app --host 0.0.0.0 --port 80"
```

* * *

### Once done

Check the status of the web app:

```powershell
az webapp show `
  --name $webAppName `
  --resource-group $resourceGroup `
  --query state
```

Point your browser at:
```
https://home-efficiency-calculator-app.azurewebsites.net/
```

### Post a request to the API:
```
curl -Method 'POST' `
  -Uri 'https://home-efficiency-calculator-app.azurewebsites.net/solar/savings/' `
  -Headers @{
        "Accept"="application/json"
        "Content-Type"="application/json"
    } `
  -Body '{
  "your_home": {
    "people_in_house": 1,
    "postcode": "6012"
  },
  "heating": {
    "main_heating_source": "Piped gas heater",
    "alternative_main_heating_source": "Heat pump",
    "heating_during_day": "Never",
    "insulation_quality": "Not well insulated"
  },
  "hot_water": {
    "hot_water_usage": "Low",
    "hot_water_heating_source": "Electric hot water cylinder",
    "alternative_hot_water_heating_source": "Hot water heat pump"
  },
  "cooktop": {
    "cooktop": "Piped gas",
    "alternative_cooktop": "Electric induction"
  },
  "driving": {
    "vehicle_size": "Small",
    "km_per_week": "200",
    "vehicle_type": "Petrol",
    "alternative_vehicle_type": "Electric"
  }
}' `
-OutFile 'response.json'
```


Step 7: Update the Web App with New Code Changes
------------------------------------------------

Whenever you have new code changes you want to deploy, you will:

1.  **Increment** the image version tag (for example, from `home-efficiency-calculator:0.2.0` to `home-efficiency-calculator:0.2.1`).

2.  **Build** and **push** the new container to your Azure Container Registry.

3.  **Switch** the Azure Web App’s container to the newly pushed version.


Below is an example workflow.

### 7.1 Update the version tag in your variables

```powershell
$resourceGroup = "eeca-rg-DWBI-dev-aue"
$acrName = "eecaacrdwbidevaue"
$location = "australiaeast"
$appServicePlan = "home-efficiency-plan"
$webAppName = "home-efficiency-calculator-app"
$loginServer = az acr show -n $acrName --query loginServer --output tsv
$acrPassword = az acr credential show -n $acrName --query "passwords[0].value" -o tsv
# Example of new version
$image = "home-efficiency-calculator:0.2.0"
$imageTag = "$loginServer/$image"
```

### 7.2 Build and push the new Docker image to ACR

```powershell
# Log in again if necessary
docker login -u $acrName -p $acrPassword $loginServer

# Build the new image
docker build -t $image .

# Tag it for pushing to ACR
docker tag $image $imageTag

# Push the new image to ACR
docker push $imageTag
```

### 7.3 Point the Azure Web App to the new image and restart

```powershell
az webapp config container set `
  --name $webAppName `
  --resource-group $resourceGroup `
  --container-image-name $imageTag `
  --container-registry-url https://$loginServer `
  --container-registry-user $acrName `
  --container-registry-password $acrPassword

# Optionally, you can force a restart to ensure the new container gets pulled:
az webapp restart `
  --name $webAppName `
  --resource-group $resourceGroup
```

At this point, Azure should pull down the newly tagged container and run it with your updated code.


* * *

Teardown
--------

### 1\. Delete the App Service (the running web app)

```powershell
az webapp delete `
  --name $webAppName `
  --resource-group $resourceGroup
```

### 2\. Delete the App Service Plan

```powershell
az appservice plan delete `
  --name $appServicePlan `
  --resource-group $resourceGroup
```