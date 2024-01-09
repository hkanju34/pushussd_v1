import uuid
from datetime import datetime
import xml.etree.ElementTree as ET
import requests
from django.utils import timezone
from django.core.management.base import BaseCommand
from .vendors import vendors



#generate trans date time parameter
now = datetime.now()
ds = now.strftime("%Y-%m-%dT%H:%M:%SZ")
nowzone = now.strftime("%Y-%m-%d %H:%M:%SZ")
headers = {'Content-Type': 'application/soap+xml'}
mcom_url = 'http://10.0.80.134:9906/cws/transaction'
token_request_url = 'http://10.0.80.134:9906/systemagent'

ussd_creds = {
    "url":"http://10.0.80.116:6113/niussd/v2/",
    "auth":('mcom', 'g65!bn}gfj8G[yd2h^a')
}

def gen_trans_id():
    # Generate a unique ascending number
    unique_number = str(uuid.uuid4().int)[:10]

    # Combine the fixed string and unique number to create the transaction ID
    transaction_id = 'TUGW' + unique_number

    return transaction_id


sess_token = '''
<S:Envelope xmlns:S="http://www.w3.org/2003/05/soap-envelope" xmlns:env="http://www.w3.org/2003/05/soap-envelope">
   <env:Header />
   <S:Body>
      <ns2:SoapSystemAgentLoginRequest xmlns:ns2="http://soap.api.novatti.com/tticommon/messages">
         <header>
            <authentication>
               <agentCode>CWS</agentCode>
            </authentication>
            <version>1.0</version>
            <agentVersion>2.3.0</agentVersion>
            <agentTransactionId>{}</agentTransactionId>
            <agentTimeStamp>{}</agentTimeStamp>
         </header>
      </ns2:SoapSystemAgentLoginRequest>
   </S:Body>
</S:Envelope>'''.format(gen_trans_id(), ds)

def momo_session():
    try:
        # Send the request to retrieve the token
        response = requests.post(token_request_url, data=sess_token,headers=headers)

        # Parse the response XML to extract the token
        root = ET.fromstring(response.content)
        session_token = root.find(".//sessionToken").text
        return session_token

    except Exception as error:
        print(f'Token error: {error}')


bkcn = '''
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns0="http://soap.api.novatti.com/cws/messages" xmlns:ns1="http://soap.api.novatti.com/cws/messages" xmlns:tns="http://soap.api.novatti.com/cws/service" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
   <soap:Body>
      <ns1:SoapTransactRequest>
         <header>
            <authentication>
               <sessionToken>{}</sessionToken>
               <authDevice>
                  <key>PIN</key>
                  <identification>255738261113</identification>
                  <type>MOBILE</type>
               </authDevice>
            </authentication>
            <version>1.0</version>
            <agentVersion>1</agentVersion>
            <agentTransactionId>1372</agentTransactionId>
            <agentTimeStamp>{}</agentTimeStamp>
            <languageCode>en</languageCode>
            <languageId>27</languageId>
         </header>
         <keyValues>
            <item>
               <key>account</key>
               <value>billno</value>
            </item>
         </keyValues>
         <source>
            <walletTypeCode>SUBSCRIBER</walletTypeCode>
         </source>
         <destination>
            <msisdn>NMB_BANK</msisdn>
            <walletTypeCode>SUBSCRIBER</walletTypeCode>
         </destination>
         <amount>0.00</amount>
         <transactionTypeCode>BkIn</transactionTypeCode>
      </ns1:SoapTransactRequest>
   </soap:Body>
</soap:Envelope>
'''.format( momo_session(), ds)

selbil = '''
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://www.w3.org/2003/05/soap-envelope" xmlns:SOAP-ENC="http://www.w3.org/2003/05/soap-encoding" xmlns:ns1="http://soap.api.novatti.com/cws/messages" xmlns:ns2="http://soap.api.novatti.com/cws/types" xmlns:ns3="http://soap.api.novatti.com/types" xmlns:ns4="http://soap.api.novatti.com/tticommon/messages" xmlns:ns5="http://soap.api.novatti.com/tticommon/types" xmlns:ns6="http://soap.api.novatti.com/cws/service" xmlns:ns7="http://soap.api.novatti.com/service" xmlns:ns8="http://soap.api.novatti.com/tticommon/service" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
   <SOAP-ENV:Body>
      <ns1:SoapTransactRequest>
         <header>
            <authentication>
               <sessionToken>{}</sessionToken>
               <authDevice>
                  <key>0603</key>
                  <identification>255739310307</identification>
                  <type>MOBILE</type>
               </authDevice>
            </authentication>
            <version>1.0</version>
            <agentVersion>1</agentVersion>
            <agentTransactionId>000000000699326A01</agentTransactionId>
            <agentTimeStamp>{}</agentTimeStamp>
            <languageCode>en</languageCode>
            <languageId>27</languageId>
         </header>
         <keyValues>
            <item>
               <key>account</key>
               <value>TTCL</value>
            </item>
            <item>
               <key>msisdn</key>
               <value>255739310307</value>
            </item>
            <item>
               <key>utilitycode</key>
               <value>AXIEVA-TIGO</value>
            </item>
            <item>
               <key>utilityref</key>
               <value>0652310307</value>
            </item>
            <item>
               <key>cellid</key>
               <value>10643</value>
            </item>
         </keyValues>
         <source>
            <walletTypeCode>SUBSCRIBER</walletTypeCode>
         </source>
         <destination>
            <msisdn>AXIEVA_MSISDN</msisdn>
            <walletTypeCode>SUBSCRIBER</walletTypeCode>
         </destination>
         <amount>1000</amount>
         <transactionTypeCode>BPay</transactionTypeCode>
      </ns1:SoapTransactRequest>
   </SOAP-ENV:Body>
</SOAP-ENV:Envelope>'''.format( momo_session(), ds)


def pay_contro_num(billNo,amount,source,pin,transid):
    # Parse the XML string into an ElementTree object
    root = ET.fromstring(bkcn)

    root.find(".//agentTransactionId").text = transid
    root.find(".//item[key='account']/value").text = billNo
    root.find(".//amount").text = amount
    root.find(".//identification").text = source
    root.find(".//authDevice/key").text=pin

    # Return the modified XML as a string
    modified_xml = ET.tostring(root, encoding="unicode")
    try:
        resp = requests.post(mcom_url,data=modified_xml,headers=headers)
        try:
            root = ET.fromstring(resp.content)
            resp_code = root.find('.//resultCode').text
            resp_id = root.find('.//transactionId').text
            resp_desc = root.find('.//resultDescription').text
            return {'resp_code':resp_code,'resp_id':resp_id,'resp_desc':resp_desc}
        except (ET.ParseError, AttributeError) as err:
            print(f"Error parsing token response: {err}")
            return None

    except Exception as error:
        print(error)


def pay_sel_bill(billNo,amount,source,pin,transid,utilitycode,collectionAcc):
    root = ET.fromstring(selbil)


    root.find(".//agentTransactionId").text = transid
    root.find(".//item[key='msisdn']/value").text = source
    root.find(".//item[key='utilitycode']/value").text = utilitycode
    root.find(".//item[key='utilityref']/value").text = billNo
    root.find(".//amount").text = amount
    root.find(".//identification").text = source
    root.find(".//destination/msisdn").text=collectionAcc
    root.find(".//authDevice/key").text=pin

    # Return the modified XML as a string
    modified_xml = ET.tostring(root, encoding="unicode")
    try:
        resp = requests.post(mcom_url,data=modified_xml,headers=headers)
        try:
            root = ET.fromstring(resp.content)
            resp_code = root.find('.//resultCode').text
            resp_id = root.find('.//transactionId').text
            resp_desc = root.find('.//resultDescription').text
            return {'resp_code':resp_code,'resp_id':resp_id,'resp_desc':resp_desc}
        except (ET.ParseError, AttributeError) as err:
            print(f"Error parsing token response: {err}")
            return None

    except Exception as error:
        print(f'mcom bill trans req error: {error}')

def get_vendor_details(vendor_name):
    if vendor_name in vendors:
        vendors[vendor_name]
        ucode = vendors[vendor_name]['utilityCode']
        ucolacc = vendors[vendor_name]['collectionAcc']
        return {'ucode':ucode,'ucolacc':ucolacc}
    else:
        return 'Vendor does not exist'