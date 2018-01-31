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

///
/// This sample provides steps to define an interface for a resource
/// (properties and methods) and host this resource on the server.
///
#include "iotivity_config.h"
#include <cpp_redis/cpp_redis>
#include <functional>
#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif
#ifdef HAVE_PTHREAD_H
#include <pthread.h>
#endif
#include <mutex>
#include "OCPlatform.h"
#include "OCApi.h"
#ifdef HAVE_WINDOWS_H
#include <windows.h>
#endif

#include "ocpayload.h"

using namespace OC;
using namespace std;
namespace PH = std::placeholders;

// Set of strings for each of platform Info fields
std::string  platformId = "0A3E0D6F-DBF5-404E-8719-D6880042463A";
std::string  manufacturerName = "OCF";
std::string  manufacturerLink = "https://www.baustem.com";
std::string  modelNumber = "Model-01-01";
std::string  dateOfManufacture = "2018-01-15";
std::string  platformVersion = "Platform-01-01";
std::string  operatingSystemVersion = "Linux";
std::string  hardwareVersion = "Hardware-01-01";
std::string  firmwareVersion = "1.0";
std::string  supportLink = "https://www.baustem.com";
std::string  systemTime = "2016-01-15T11.01";

// Set of strings for each of device info fields
std::string  deviceName = "Face Recognition Sensor";
std::string  deviceType = "oic.d.sensor";
std::string  specVersion = "ocf.1.1.0";
std::vector<std::string> dataModelVersions = {"ocf.res.1.1.0", "ocf.sh.1.1.0"};
std::string  protocolIndependentID = "fa008167-3bbf-4c9d-8604-c9bcb96cb712";

// OCPlatformInfo Contains all the platform info to be stored
OCPlatformInfo platformInfo;

// Specifies secure or non-secure
// false: non-secure resource
// true: secure resource
bool isSecure = false;

// Forward declaring the entityHandler

/// This class represents a single resource named 'FaceResource'. This resource has
/// two simple properties named 'state' and 'power'

class FaceResource
{
public:
    /// Access this property from a TB client
    std::string m_name;
    std::string m_faceUri;
    std::string m_resourceType;
    std::vector<std::string> m_faces;
    bool m_value;
    OCResourceHandle m_resourceHandle;
    OCRepresentation m_faceRep;
public:
    /// Constructor
    FaceResource()
        :m_name("Baustem's face"), m_faceUri("/sensor/facerecognition"),m_resourceType("oic.r.sensor.face"),
                m_resourceHandle(nullptr){
        // Initialize representation
        m_faceRep.setUri(m_faceUri);
        m_faces.clear();
        m_value = false;
    }

    /* Note that this does not need to be a member function: for classes you do not have
    access to, you can accomplish this with a free function: */

    /// This function internally calls registerResource API.
    void createResource()
    {
        //URI of the resource
        std::string resourceURI = m_faceUri;
        //resource type name. In this case, it is light
        std::string resourceTypeName = m_resourceType;
        // resource interface.
        std::string resourceInterface = DEFAULT_INTERFACE;

        // OCResourceProperty is defined ocstack.h
        uint8_t resourceProperty;
        if(isSecure)
        {
            resourceProperty = OC_DISCOVERABLE | OC_OBSERVABLE | OC_SECURE;
        }
        else
        {
            resourceProperty = OC_DISCOVERABLE | OC_OBSERVABLE;
        }
        EntityHandler cb = std::bind(&FaceResource::entityHandler, this,PH::_1);

        // This will internally create and register the resource.
        OCStackResult result = OCPlatform::registerResource(
                                    m_resourceHandle, resourceURI, resourceTypeName,
                                    resourceInterface, cb, resourceProperty);

        if (OC_STACK_OK != result)
        {
            cout << "Resource creation was unsuccessful\n";
        }
    }

    OCResourceHandle getHandle()
    {
        return m_resourceHandle;
    }

    // gets the updated representation.
    // Updates the representation with latest internal state before
    // sending out.
    OCRepresentation get()
    {
        std::vector<std::string> rt = {m_resourceType};
        m_faceRep.setValue<std::vector<std::string>>("rt", rt);
        std::vector<std::string> inf = {DEFAULT_INTERFACE, LINK_INTERFACE};
        m_faceRep.setValue<std::vector<std::string>>("if", inf);
        m_faceRep.setValue<std::vector<std::string>>("face", m_faces);
        m_faceRep.setValue("value", m_value);
        return m_faceRep;
    }

    void addType(const std::string& type) const
    {
        OCStackResult result = OCPlatform::bindTypeToResource(m_resourceHandle, type);
        if (OC_STACK_OK != result)
        {
            cout << "Binding TypeName to Resource was unsuccessful\n";
        }
    }

    void addInterface(const std::string& iface) const
    {
        OCStackResult result = OCPlatform::bindInterfaceToResource(m_resourceHandle, iface);
        if (OC_STACK_OK != result)
        {
            cout << "Binding TypeName to Resource was unsuccessful\n";
        }
    }

private:
// This is just a sample implementation of entity handler.
// Entity handler can be implemented in several ways by the manufacturer
OCEntityHandlerResult entityHandler(std::shared_ptr<OCResourceRequest> request)
{
    cout << "\tIn Server CPP entity handler:\n";
    OCEntityHandlerResult ehResult = OC_EH_ERROR;
    if(request)
    {
        // Get the request type and request flag
        std::string requestType = request->getRequestType();
        int requestFlag = request->getRequestHandlerFlag();

        if(requestFlag & RequestHandlerFlag::RequestFlag)
        {
            cout << "\t\trequestFlag : Request\n";
            auto pResponse = std::make_shared<OC::OCResourceResponse>();
            pResponse->setRequestHandle(request->getRequestHandle());
            pResponse->setResourceHandle(request->getResourceHandle());

            // Check for query params (if any)
            QueryParamsMap queries = request->getQueryParameters();

            if (!queries.empty())
            {
                std::cout << "\nQuery processing upto entityHandler" << std::endl;
            }
            for (auto it : queries)
            {
                std::cout << "Query key: " << it.first << " value : " << it.second
                        << std:: endl;
            }

            // If the request type is GET
            if(requestType == "GET")
            {
                cout << "\t\t\trequestType : GET\n";
                {

                    pResponse->setResponseResult(OC_EH_OK);
                    pResponse->setResourceRepresentation(get());
                    if(OC_STACK_OK == OCPlatform::sendResponse(pResponse))
                    {
                        ehResult = OC_EH_OK;
                    }
                }
            }
            else
            {
                ehResult = OC_EH_FORBIDDEN;;
                cout << "Not Supported Request Type" << requestType << endl;
            }
        }
    }
    else
    {
        std::cout << "Request invalid" << std::endl;
    }

    return ehResult;
}

};

void DeletePlatformInfo()
{
    delete[] platformInfo.platformID;
    delete[] platformInfo.manufacturerName;
    delete[] platformInfo.manufacturerUrl;
    delete[] platformInfo.modelNumber;
    delete[] platformInfo.dateOfManufacture;
    delete[] platformInfo.platformVersion;
    delete[] platformInfo.operatingSystemVersion;
    delete[] platformInfo.hardwareVersion;
    delete[] platformInfo.firmwareVersion;
    delete[] platformInfo.supportUrl;
    delete[] platformInfo.systemTime;
}

void DuplicateString(char ** targetString, std::string sourceString)
{
    *targetString = new char[sourceString.length() + 1];
    strncpy(*targetString, sourceString.c_str(), (sourceString.length() + 1));
}

OCStackResult SetPlatformInfo(std::string platformID, std::string manufacturerName,
        std::string manufacturerUrl, std::string modelNumber, std::string dateOfManufacture,
        std::string platformVersion, std::string operatingSystemVersion,
        std::string hardwareVersion, std::string firmwareVersion, std::string supportUrl,
        std::string systemTime)
{
    DuplicateString(&platformInfo.platformID, platformID);
    DuplicateString(&platformInfo.manufacturerName, manufacturerName);
    DuplicateString(&platformInfo.manufacturerUrl, manufacturerUrl);
    DuplicateString(&platformInfo.modelNumber, modelNumber);
    DuplicateString(&platformInfo.dateOfManufacture, dateOfManufacture);
    DuplicateString(&platformInfo.platformVersion, platformVersion);
    DuplicateString(&platformInfo.operatingSystemVersion, operatingSystemVersion);
    DuplicateString(&platformInfo.hardwareVersion, hardwareVersion);
    DuplicateString(&platformInfo.firmwareVersion, firmwareVersion);
    DuplicateString(&platformInfo.supportUrl, supportUrl);
    DuplicateString(&platformInfo.systemTime, systemTime);

    return OC_STACK_OK;
}

OCStackResult SetDeviceInfo()
{
    OCStackResult result = OC_STACK_ERROR;

    OCResourceHandle handle = OCGetResourceHandleAtUri(OC_RSRVD_DEVICE_URI);
    if (handle == NULL)
    {
        cout << "Failed to find resource " << OC_RSRVD_DEVICE_URI << endl;
        return result;
    }

    result = OCBindResourceTypeToResource(handle, deviceType.c_str());
    if (result != OC_STACK_OK)
    {
        cout << "Failed to add device type" << endl;
        return result;
    }

    result = OCPlatform::setPropertyValue(PAYLOAD_TYPE_DEVICE, OC_RSRVD_DEVICE_NAME, deviceName);
    if (result != OC_STACK_OK)
    {
        cout << "Failed to set device name" << endl;
        return result;
    }

    result = OCPlatform::setPropertyValue(PAYLOAD_TYPE_DEVICE, OC_RSRVD_DATA_MODEL_VERSION,
                                          dataModelVersions);
    if (result != OC_STACK_OK)
    {
        cout << "Failed to set data model versions" << endl;
        return result;
    }

    result = OCPlatform::setPropertyValue(PAYLOAD_TYPE_DEVICE, OC_RSRVD_SPEC_VERSION, specVersion);
    if (result != OC_STACK_OK)
    {
        cout << "Failed to set spec version" << endl;
        return result;
    }

    result = OCPlatform::setPropertyValue(PAYLOAD_TYPE_DEVICE, OC_RSRVD_PROTOCOL_INDEPENDENT_ID,
                                          protocolIndependentID);
    if (result != OC_STACK_OK)
    {
        cout << "Failed to set piid" << endl;
        return result;
    }

    return OC_STACK_OK;
}

int main(int argc, char* argv[])
{
    (void)argc;
    (void)argv;
    //redis clinet
    cpp_redis::client client;

    client.connect("127.0.0.1", 6379, [](const std::string& host, std::size_t port, cpp_redis::client::connect_state status) {
        if (status == cpp_redis::client::connect_state::dropped) {
            std::cout << "client disconnected from " << host << ":" << port << std::endl;
        }
    });
    // Create PlatformConfig object
    PlatformConfig cfg {
        OC::ServiceType::InProc,
        OC::ModeType::Server,
        NULL
    };

    cfg.transportType = static_cast<OCTransportAdapter>(OCTransportAdapter::OC_ADAPTER_IP | 
                                                        OCTransportAdapter::OC_ADAPTER_TCP);
    cfg.QoS = OC::QualityOfService::LowQos;

    OCPlatform::Configure(cfg);
    OC_VERIFY(OCPlatform::start() == OC_STACK_OK);
    std::cout << "Starting server & setting platform info\n";

    OCStackResult result = SetPlatformInfo(platformId, manufacturerName, manufacturerLink,
            modelNumber, dateOfManufacture, platformVersion, operatingSystemVersion,
            hardwareVersion, firmwareVersion, supportLink, systemTime);

    result = OCPlatform::registerPlatformInfo(platformInfo);

    if (result != OC_STACK_OK)
    {
        std::cout << "Platform Registration failed\n";
        return -1;
    }

    result = SetDeviceInfo();

    if (result != OC_STACK_OK)
    {
        std::cout << "Device Registration failed\n";
        return -1;
    }

    try
    {
        // Create the instance of the resource class
        // (in this case instance of class 'FaceResource').
        FaceResource myFace;

        // Invoke createResource function of class light.
        myFace.createResource();
        std::cout << "Created resource." << std::endl;

        myFace.addInterface(std::string(LINK_INTERFACE));
        std::cout << "Added Interface and Type" << std::endl;

        DeletePlatformInfo();

        // A condition variable will free the mutex it is given, then do a non-
        // intensive block until 'notify' is called on it.  In this case, since we
        // don't ever call cv.notify, this should be a non-processor intensive version
        // of while(true);
	    cpp_redis::reply lastreply("|", cpp_redis::reply::string_type::simple_string);
        std::vector<std::string> myface;
        while(1){
            auto get = client.get("face");
            client.sync_commit();
            cpp_redis::reply reply = get.get();
            if (reply.is_string()
                && (lastreply.as_string().find("|") >= 0 && reply.as_string().find("|") >= 0)
                && lastreply.as_string().substr(lastreply.as_string().find("|")) != reply.as_string().substr(reply.as_string().find("|"))) {
                std::cout << "get face: " << reply << ", lastreply:" << lastreply << std::endl;
		        lastreply = reply;
                myface.clear();
                std::string tmp = reply.as_string();
                std::string::size_type pos1, pos2;
                pos2 = tmp.find('#');
                pos1 = tmp.find('|') + 1;
                while(pos2 != -1 && pos1 != 0 && std::string::npos != pos2)
                {
                    myface.push_back(tmp.substr(pos1, pos2-pos1));
                    pos1 = pos2 + 1;
                    pos2 = tmp.find('#', pos1);
                }
                if(pos1 != 0 && pos1 != tmp.length())
                    myface.push_back(tmp.substr(pos1));
            
                for (auto &face : myface){
                    std::cout << "face = " << face << std::endl;
                }
                myFace.m_value = true;
	        }else{
                //no matter the face detected is all the same or no face detected at all
                myFace.m_value = false;
            }
            if(myface.size() > 0 && myFace.m_value){
                myFace.m_faces.clear();
                myFace.m_faces = myface;
                myFace.m_value = true;
                //notify all observer
                std::cout << "notify all observer" << std::endl;
                OCPlatform::notifyAllObservers(myFace.m_resourceHandle);
            }
            usleep(1000*1000);
        }
    }
    catch(OCException &e)
    {
        std::cout << "OCException in main : " << e.what() << endl;
    }

    OC_VERIFY(OCPlatform::stop() == OC_STACK_OK);

    return 0;
}
