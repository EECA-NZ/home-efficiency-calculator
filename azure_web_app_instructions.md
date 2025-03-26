Step 1: Set Variables
---------------------

```powershell
$resourceGroup = "eeca-rg-DWBI-dev-aue"
$acrName = "eecaacrdwbidevaue"
$location = "australiaeast"
$appServicePlan = "home-efficiency-plan"
$webAppName = "home-efficiency-calculator-app"
$image = "home-efficiency-calculator:0.2.0"
$loginServer = az acr show -n $acrName --query loginServer --output tsv
$imageTag = "$loginServer/$image"
$acrPassword = az acr credential show -n $acrName --query "passwords[0].value" -o tsv
```

Step 2: Ensure the Docker image is built and pushed to the Azure Container Registry
---------------------

```powershell
docker login -u $acrName -p $acrPassword $loginServer
docker build -t $image .
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
  --docker-custom-image-name $imageTag `
  --docker-registry-server-url https://$loginServer `
  --docker-registry-server-user $acrName `
  --docker-registry-server-password $acrPassword
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
https://home-efficiency-calculator-app.azurewebsites.net/docs
```

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
