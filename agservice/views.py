from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
import json
from rest_framework.views import APIView
from .models import Payload
from rest_framework.permissions import IsAuthenticated
from agservice.authentication import ExpiringTokenAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from .payloads import *
import requests
import threading
import traceback
import sys
from .models import Payload
from .vendors import vendors
from django.contrib.auth.models import User

# Create your views here.
#DB calls for operations
def db_updates(tugwid,udate,mcom_id,mcom_code,mcom_desc):
    try:
        my_db = Payload.objects.filter(tugw_trans_id=tugwid)
        my_db.update(trans_status=1,
                    updated_date=udate,
                    mcom_desc = mcom_desc,
                    mcom_id = mcom_id,
                    mcom_status = mcom_code
                    )
    except Exception as update_err:
        print(f'DB update error: {update_err}')    
    

class Pushagr(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        user = request.user
        # Process the payload and extract the required information
        client_id = request.data.get('clientId')
        tugw_trans_id = gen_trans_id()
        trans_date = request.data.get('transDate')
        msisdn = request.data.get('msisdn')
        bill_no = request.data.get('billNo')
        bill_disc = request.data.get('billDisc')
        amount = request.data.get('amount')
        currency = request.data.get('currency')
        trans_code = request.data.get('transCode')
        client_trans_id = request.data.get('reqId')
        print(client_id)

        # Save the payload to the database
        try:
            payload = Payload.objects.create(
                ptran_sdate=trans_date,
                client_id = client_id,
                msisdn=msisdn,
                bill_no=bill_no,
                bill_disc=bill_disc,
                amount=amount,
                currency=currency,
                trans_code=trans_code,
                client_trans_id=client_trans_id,
                tugw_trans_id=tugw_trans_id,
                trans_status=0  # Set the initial status as pending
            )
        except Exception as db_error:
            print(f'DB Error: {db_error}')
            return Response({"error": "internal system error"})

        if (trans_code == "BCN" or trans_code == "SBP") and (client_id in vendors):
            # Generate the acknowledgement response
            ack_response = {
                "reqId": client_trans_id,
                "ttclRespId": tugw_trans_id,
                "statusCode": "00",
                "respDesc": "received Successfully"
            }

            # Respond with the ack_response immediately
            threading.Thread(target=self.process_pin_request, args=(client_trans_id, msisdn, bill_no, amount, tugw_trans_id, trans_code, bill_disc,client_id)).start()
            return Response(ack_response)

        return Response({"reqId": client_trans_id, 
                         "ttclRespId": tugw_trans_id,
                         "statusCode": "01",
                         "respDesc": "ERROR, please recheck you payload Request"
                         })

    def process_pin_request(self, trans_id, msisdn, bill_no, amount, tugw_trans_id, trans_code,bill_disc,client_id):
        pin_request_payload = {
        "header": {},
        "request": {
            "type": "PROMPT_FINAL",
            "msisdn": msisdn,
            "message": "Please Enter PIN to make payment of TZS:{}  for BillNo: {}:{}".format(amount,bill_no,bill_disc),
            "final_message": "Thank you for your response. You will receive a message shortly.",
            "session_id": trans_id
        }
        }

        try:
            response = requests.post(ussd_creds['url'], json=pin_request_payload, auth=ussd_creds['auth'])
            response.raise_for_status()
        except Exception as pin_error:
            print(f'PIN request error: {pin_error}')
            traceback.print_exc(file=sys.stdout)
            return Response({"error": "internal system error"})

        if response.status_code == 200:
            response_content = response.content.decode('utf-8')
            json_resp = json.loads(response_content)

            if 'response' in json_resp and 'message' in json_resp['response']:
                pin = json_resp['response']['message']
            else:
                pin = None

            if 'header' in json_resp and 'result' in json_resp['header'] and 'description' in json_resp['header']['result']:
                pin_resp_desc = json_resp['header']['result']['description']
            else:
                pin_resp_desc = None

            if pin is not None and pin_resp_desc is not None:

                 #Execute push for CN bills
                if json_resp['header']['result']['code'] == 0 and trans_code == "BCN":
                    try:
                        bkin_resp = pay_contro_num(bill_no, amount, msisdn, pin, tugw_trans_id)
                        if bkin_resp:
                            resp_code = bkin_resp['resp_code']
                            resp_id = bkin_resp['resp_id']
                            resp_desc = bkin_resp['resp_desc']
                            if resp_code == '0':
                                db_updates(tugw_trans_id,nowzone,resp_id,resp_code,resp_desc)
                                print(f'the row for tugw: {tugw_trans_id} was updated successfful')

                    except Exception as bkcn_error:
                        print(f'BkCn error: {bkcn_error}')
                 
                 #Execute push for non CN bills      
                elif json_resp['header']['result']['code'] == 0 and trans_code == "SBP":
                    try:
                        get_vendor = get_vendor_details(client_id)
                        if get_vendor:
                            utilitycode = get_vendor['ucode']
                            collectionAcc = get_vendor['ucolacc']
                            
                            try:
                                sel_resp = pay_sel_bill(bill_no, amount, msisdn, pin, tugw_trans_id,utilitycode,collectionAcc)
                                if sel_resp:
                                    resp_code = sel_resp['resp_code']
                                    resp_id = sel_resp['resp_id']
                                    resp_desc = sel_resp['resp_desc']
                                    if resp_code == '0':
                                        try:
                                            db_updates(tugw_trans_id,nowzone,resp_id,resp_code,resp_desc)
                                            print(f'the row for tugw: {tugw_trans_id} was updated successfful')
                                        except Exception as seldb_err:
                                            print(f'SBP DB not updated error: {seldb_err}')

                            except Exception as mcom_err:
                                print(f'Sel mcom error: {mcom_err}')
                    except Exception as sel_error:
                        print(f'Sell bill error: {sel_error}')
                else:
                    print(pin_resp_desc)
            else:
                print("Invalid JSON response structure")

        return response
    

class PushMngnt(APIView):
     permission_classes = [IsAuthenticated]
     
     def post(self, request, *args, **kwargs):
        user = request.user
        # Process the payload and extract the required information
        vendor_name = request.data.get('vendorName')
        vendor_ucode = request.data.get('vendorUtCode')
        vendor_collacc = request.data.get('vendorCollAcc')
        print(f'{vendor_name}:: {vendor_ucode} :: {vendor_collacc}')

        vendor_resp={
            'result_code':"001",
            'result_desc':'successfull added'
        }
        vendor_resp_error={
            'result_code':"101",
            'result_desc':'Error trying to add vendor'
            }

        
        if vendor_name not in vendors:
            # Generate the acknowledgement response
            try:
                vendors[vendor_name] = {
                    'utilityCode': vendor_ucode,
                    'collectionAcc': vendor_collacc
                }
            except Exception as vnd_err:
                print(f'Add vendor error: {vnd_err}')
                return Response(vendor_resp)

            # Respond with the ack_response immediately
            return Response(vendor_resp)

        return Response(vendor_resp_error)

class AddUser(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user1 = request.user
        # Retrieve user data from the request body
        username = request.data.get('username')
        password = request.data.get('password')
        # Add more fields as needed

        useradd_resp={
            'result_code':"001",
            'result_desc':'successfull added'
        }
        useradd_resp_error={
            'result_code':"101",
            'result_desc':'Error trying to add user'
            }
        
        # Create the user
        try:
            user = User.objects.create_user(username=username, password=password)
            # Add more fields to the user object if necessary
            if user:
                return Response(useradd_resp)
        except Exception as user_err:
            print(f'add user error: {user_err}')

        # Return a success response
        return Response(useradd_resp_error)

@csrf_exempt
def trans_records(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
        
        print(start_datetime)
        queryset = Payload.objects.filter(created_date__range=(start_datetime, end_datetime))
        
        # Create a list of JSON objects representing the model details
        results = []
        for obj in queryset:
            result = {
                'client_id': obj.client_id,
                'client_date': obj.ptran_sdate,
                'msisdn': obj.msisdn,
                'Bill_Number': obj.bill_no,
                'bill_disc': obj.bill_disc,
                'amount': obj.amount,
                'currency': obj.currency,
                'trans_code': obj.trans_code,
                'client_trans_id': obj.client_trans_id,
                'tugw_trans_id': obj.tugw_trans_id,
                'trans_status': obj.trans_status,
                'created_date': obj.created_date,
                'updated_date': obj.updated_date,
                'mcom_id': obj.mcom_id,
                'mcom_status': obj.mcom_status,
                'mcom_desc': obj.mcom_desc,
                # Include other fields of your model in the JSON response
            }
            results.append(result)
        
        return JsonResponse(results, safe=False)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)