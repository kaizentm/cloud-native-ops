# Secured Argo CD Dashboard With Azure AD 

Follow instructions on enabling [OIDC auth flow](https://argoproj.github.io/argo-cd/operator-manual/user-management/microsoft/#azure-ad-app-registration-auth-using-oidc) for ArgoCD Dashboard. 
 
## Exposing Argo CD Dashboard and REST API over HTTPS with Kubernetes Ingress. 

Pre-requisites: 
1. Azure CLI 
1. Helm

<br>

1. Create a static public IP with Azure CLI

    ```bash
    az network public-ip create --resource-group <aks_node_resource_group> --name <public_ip_name> --sku Standard --allocation-method static --query publicIp.ipAddress -o tsv
    ```
    Note the static public IP created  
    
1. Install Ingress controller

    ```bash
    # Create a namespace for your ingress resources
    kubectl create namespace ingress-nginx
    
    # Add the ingress-nginx repository
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    
    # Use Helm to deploy an NGINX ingress controller
    helm install nginx-ingress ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --set controller.replicaCount=2 \
        --set controller.nodeSelector."beta\.kubernetes\.io/os"=linux \
        --set defaultBackend.nodeSelector."beta\.kubernetes\.io/os"=linux \
        --set controller.service.loadBalancerIP="STATIC_IP" \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"="argocdashboard"
    ```
    This will install ingress controller and assign a DNS label `argocdashboard` to static public ip created in previous step

    Ensure the DNS label is applied to public ip with below:

    ```bash
    az network public-ip list --resource-group <aks_node_resource_group> --query "[?name=='public_ip_name'].[dnsSettings.fqdn]" -o tsv    
    ```  

    **Note**: Ensure the DNS label created above is the one used in 
     1. OIDC configuration `kubectl get cm argocd-cm -n argocd --output="jsonpath={.data.url}"`    
     1. Azure AD app redrect url e.g. https://dns_name/auth/callback
         

1. Installing and Configuring Cert-Manager

     Install cert-manager and its Custom Resource Definitions (CRDs) like Issuers and ClusterIssuers by following the official installation instructions. Note that a namespace called cert-manager will be created into which the cert-manager objects will be created:
    
    ```bash
    # Label the cert-manager namespace to disable resource validation
    kubectl label namespace ingress-nginx cert-manager.io/disable-validation=true
    
    # Add the Jetstack Helm repository
    helm repo add jetstack https://charts.jetstack.io
    
    # Update your local Helm chart repository cache
    helm repo update
    
    # Install the cert-manager Helm chart
    helm install \
    cert-manager \
    --namespace ingress-nginx \
    --version v0.16.1 \
    --set installCRDs=true \
    --set nodeSelector."beta\.kubernetes\.io/os"=linux \
    jetstack/cert-manager
    ```
    To verify our installation, check the cert-manager Namespace for running pods:

    ```bash
    kubectl get pods --namespace ingress-nginx
    ```
1. Create a CA cluster issuer

    Create Staging Issuer **staging_issuer.yaml** with below yaml and install using `kubectl create -f staging_issuer.yaml`
    ``` bash
    apiVersion: cert-manager.io/v1alpha2
    kind: ClusterIssuer
    metadata:
     name: letsencrypt-staging
     namespace: ingress-nginx
    spec:
     acme:
       # The ACME server URL
       server: https://acme-staging-v02.api.letsencrypt.org/directory
       # Email address used for ACME registration
       email: your_email_address_here
       # Name of a secret used to store the ACME account private key
       privateKeySecretRef:
         name: letsencrypt-staging
       # Enable the HTTP-01 challenge provider
       solvers:
       - http01:
           ingress:
             class:  nginx
    
    ```

    Create Prod Issuer **prod_issuer.yaml** with below yaml and install using `kubectl create -f prod_issuer.yaml`
    ```bash
    apiVersion: cert-manager.io/v1alpha2
    kind: ClusterIssuer
    metadata:
      name: letsencrypt-prod
      namespace: ingress-nginx
    spec:
      acme:
        # The ACME server URL
        server: https://acme-v02.api.letsencrypt.org/directory
        # Email address used for ACME registration
        email: your_email_address_here
        # Name of a secret used to store the ACME account private key
        privateKeySecretRef:
          name: letsencrypt-prod
        # Enable the HTTP-01 challenge provider
        solvers:
        - http01:
            ingress:
              class: nginx
    ```

1. Create Ingress Route:
    
    ```bash
    apiVersion: extensions/v1beta1
    kind: Ingress
    metadata:
      name: argocd-server-ingress
      namespace: argocd
      annotations:
        cert-manager.io/cluster-issuer: letsencrypt-prod
        kubernetes.io/ingress.class: nginx
        kubernetes.io/tls-acme: "true"
        nginx.ingress.kubernetes.io/ssl-passthrough: "true"
        nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
        
    spec:
      rules:
      - host: <DNS_NAME>
        http:
          paths:
          - backend:
              serviceName: argocd-server
              servicePort: https
            path: /
      tls:
      - hosts:
        - <DNS_NAME>
        secretName: argocd-secret # do not change, this is provided by Argo CD
    ``` 


## Accessing Argo CD REST API

   Swagger docs for ArgoCD REST api can be found by setting the path to /swagger-ui in your Argo CD UI's. E.g. https://dns_name/swagger-ui.
    
   API tokens can be generated at from ArgoCD Dashboard :- Settings -> Accounts -> Tokens 

    ```bash
    $ curl $ARGOCD_SERVER/api/v1/applications -H "Authorization: Bearer $ARGOCD_TOKEN" 
    {"metadata":{"selfLink":"/apis/argoproj.io/v1alpha1/namespaces/argocd/applications","resourceVersion":"37755"},"items":...}
    ```