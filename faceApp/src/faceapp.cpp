//******************************************************************
//
// Copyright 2014 Intel Mobile Communications GmbH All Rights Reserved.
//
//-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
//-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

// OCClient.cpp : Defines the entry point for the console application.
//
#include "iotivity_config.h"
#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif
#ifdef HAVE_PTHREAD_H
#include <pthread.h>
#endif
#ifdef HAVE_WINDOWS_H
#include <Windows.h>
#endif
#include <string>
#include <map>
#include <cstdlib>
#include <mutex>
#include <algorithm>
#include "OCPlatform.h"
#include "OCApi.h"

using namespace OC;

typedef std::map<OCResourceIdentifier, std::shared_ptr<OCResource>> DiscoveredResourceMap;

DiscoveredResourceMap discoveredResources;
std::shared_ptr<OCResource> curResource;
std::shared_ptr<OCResource> faceResource;
static ObserveType OBSERVE_TYPE_TO_USE = ObserveType::Observe;
static OCConnectivityType TRANSPORT_TYPE_TO_USE = OCConnectivityType::CT_ADAPTER_IP;
std::mutex curResourceLock;
std::vector<std::string> knownfaces = {"fengping"};

void onPost2(const HeaderOptions& /*headerOptions*/,
             const OCRepresentation& rep, const int eCode);

void onObserve(const HeaderOptions /*headerOptions*/, const OCRepresentation& rep,
                    const int& eCode, const int& sequenceNumber)
{
    try
    {
        if(eCode == OC_STACK_OK && sequenceNumber <= MAX_SEQUENCE_NUMBER)
        {
            if(sequenceNumber == OC_OBSERVE_REGISTER)
            {
                std::cout << "Observe registration action is successful" << std::endl;
            }
            bool value = false;
            rep.getValue("value", value);
            if(value){
                /*get the faces*/
                std::vector<std::string> faces;
                rep.getValue("face", faces);
                for(auto &face : faces){
                    if(std::find(knownfaces.begin(), knownfaces.end(), face) != knownfaces.end()){
                        //found face in known, unlock the door
                        OCRepresentation rep2;
                        rep2.setValue<std::string>("lockState", "Unlocked");
                        if(curResource)
                            curResource->post(rep2, QueryParamsMap(), &onPost2);
                    } else{
                        std::cout << "face: " << face << " not allowd to open the door" << std::endl;
                    }
                }
            }
        }
        else
        {
            if(eCode == OC_STACK_OK)
            {
                std::cout << "No observe option header is returned in the response." << std::endl;
                std::cout << "For a registration request, it means the registration failed"
                        << std::endl;
                std::cout << "For a cancelation request, it means the cancelation was successful"
                        << std::endl;
            }
            else
            {
                std::cout << "onObserve Response error: " << eCode << std::endl;
                std::exit(-1);
            }
        }
    }
    catch(std::exception& e)
    {
        std::cout << "Exception: " << e.what() << " in onObserve" << std::endl;
    }

}

void onPost2(const HeaderOptions& /*headerOptions*/,
        const OCRepresentation&, const int eCode)
{
    try
    {
        if(eCode == OC_STACK_OK || eCode == OC_STACK_RESOURCE_CREATED
                || eCode == OC_STACK_RESOURCE_CHANGED)
        {
            std::cout << "POST request was successful" << std::endl;
        }
        else
        {
            std::cout << "onPost2 Response error: " << eCode << std::endl;
        }
    }
    catch(std::exception& e)
    {
        std::cout << "Exception: " << e.what() << " in onPost2" << std::endl;
    }

}
// Callback handler on GET request
void onGet(const HeaderOptions& /*headerOptions*/, const OCRepresentation& rep, const int eCode)
{
    try
    {
        if(eCode == OC_STACK_OK)
        {
            std::cout << "GET request was successful" << std::endl;
            std::cout << "Resource URI: " << rep.getUri() << std::endl;

            OCRepresentation rep2;
            rep2.setValue("lockState", "Unlocked");
            if(curResource)
                curResource->post(rep2, QueryParamsMap(), &onPost2);
        }
        else
        {
            std::cout << "onGET Response error: " << eCode << std::endl;
        }
    }
    catch(std::exception& e)
    {
        std::cout << "Exception: " << e.what() << " in onGet" << std::endl;
    }
}

// Local function to get representation of light resource
void getFaceRepresentation(std::shared_ptr<OCResource> resource)
{
    if(resource)
    {
        std::cout << "Getting Face Representation..."<<std::endl;
        // Invoke resource's get API with the callback parameter

        resource->get(QueryParamsMap(), &onGet);
    }
}
// Callback to found resources
void foundResource(std::shared_ptr<OCResource> resource)
{
    std::string resourceURI;
    std::string hostAddress;
    try
    {
        {
            std::lock_guard<std::mutex> lock(curResourceLock);
            if(discoveredResources.find(resource->uniqueIdentifier()) == discoveredResources.end())
            {
                discoveredResources[resource->uniqueIdentifier()] = resource;
            }
            else
            {
                return;
            }
        }

        // Do some operations with resource object.
        if(resource)
        {
            for(auto &resourceTypes : resource->getResourceTypes())
            {
                if(resourceTypes == "oic.r.lock.status" && !curResource){
                    std::cout << "door lock resource: " << resource->host() << resource->uri() << std::endl;
                    curResource = resource;
                    //get the face value now to check open the door or not
                    if(faceResource)
                        getFaceRepresentation(faceResource);
                }else if(resourceTypes == "oic.r.sensor.face" && !faceResource){
                    std::cout << "face sensor resource: " << resource->host() << resource->uri() << std::endl;
                    resource->observe(OBSERVE_TYPE_TO_USE, QueryParamsMap(), &onObserve);
                    faceResource = resource;
                }
            }
        }

    }
    catch(std::exception& e)
    {
        std::cerr << "Exception in foundResource: "<< e.what() << std::endl;
    }
}

int main(int argc, char* argv[]) {
    (void)argc;
    (void)argv;
    std::ostringstream requestURI;

    // Create PlatformConfig object
    PlatformConfig cfg {
        OC::ServiceType::InProc,
        OC::ModeType::Both,
        NULL
    };

    cfg.transportType = static_cast<OCTransportAdapter>(OCTransportAdapter::OC_ADAPTER_IP | 
                                                        OCTransportAdapter::OC_ADAPTER_TCP);
    cfg.QoS = OC::QualityOfService::HighQos;

    OCPlatform::Configure(cfg);
    try
    {
        OC_VERIFY(OCPlatform::start() == OC_STACK_OK);

        // makes it so that all boolean values are printed as 'true/false' in this stream
        std::cout.setf(std::ios::boolalpha);
        // Find all resources
        requestURI << OC_RSRVD_WELL_KNOWN_URI;// << "?rt=core.light";

        do {
            OCPlatform::findResource("", requestURI.str(),
                                     CT_DEFAULT, &foundResource);
            std::cout << "Finding Resource... " << std::endl;
            usleep(5000*1000);
        }while(true);

        // Perform platform clean up.
        OC_VERIFY(OCPlatform::stop() == OC_STACK_OK);

    }catch(OCException& e)
    {
        oclog() << "Exception in main: "<<e.what();
    }

    return 0;
}


