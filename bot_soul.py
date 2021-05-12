import discord
import requests
import pandas as pd
import datetime
import copy
import argparse
from hashlib import sha256
import nest_asyncio
import time
from dotenv import load_dotenv
from os import getenv

client = discord.Client()
load_dotenv()

async def slot_finder():
    district_id = getenv("district_id")
    date = datetime.date.today().strftime('%d-%m-%y')
    try:
        request_url = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id=" + str(district_id) + "&date=" + str(date)
        request = requests.get(request_url, headers = request_header)
        if request.status_code == 200:
            data = request.json()
            data = data.get("centers")
            
            df = pd.json_normalize(data, record_path="sessions",meta = ["name","block_name","pincode","lat","long"])
            
            fields = ["name","block_name","pincode","lat","long","date","min_age_limit","available_capacity","vaccine"]
            flat_data = df[fields]
            select_data = flat_data[(flat_data.min_age_limit > 18) & (flat_data.available_capacity > 0)]
            fields = ["name", "block_name","pincode","date","available_capacity", "vaccine"]
            
            select_data = select_data[fields]
            data_json = select_data.to_json(orient = 'records')
            global last_status
            last_status = "Deeply sorry. It's a No" if select_data.empty else "data_json"
            
            
            if select_data.empty:
                print("No slots")
            else:
                await post_outputs(f"Slot availability in Pune as of {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                await post_outputs(data_json)
                
                
            beneficiaries_list = requests.get(url = "https://cdn-api.co-vin.in/api/v2/appointment/beneficiaries", headers=request_header)
            if beneficiaries_list.status_code != 200:
                await post_outputs("Token expired. Regenerating OTP..")
                await generate_token_OTP(mobile, base_request_header)
            else:
                time.sleep(15)
                await slot_finder()
                
        else:
            await post_outputs("Error while finding slot", request.status_code)
    except Exception as err:
        await post_outputs(err)

async def post_outputs(op):
    await client.wait_until_ready()
    channel_id = getenv("channel_id")
    channel = client.get_channel(int(channel_id))
    await channel.send(op)
    return 

async def generate_token_OTP(mobile, base_request_header):
    """
    This function generate OTP and returns a new token
    """
    try:
        data = {"mobile": mobile,
                "secret": "U2FsdGVkX1+z/4Nr9nta+2DrVJSv7KS6VoQUSQ1ZXYDx/CJUkWxFYG6P3iM/VW+6jLQ9RDQVzp/RcZ8kbT41xw=="
        }
        global txnId
        txnId = requests.post(url='https://cdn-api.co-vin.in/api/v2/auth/generateMobileOTP', json=data, headers=base_request_header)

        if txnId.status_code == 200:
            await post_outputs(f"Successfully requested OTP for mobile number at {datetime.datetime.today()}..")
            txnId = txnId.json()['txnId']
        
            await post_outputs("Enter the OTP received in your mobile")
            
        else:
            await post_outputs('Unable to Generate OTP')
            await post_outputs(txnId.status_code, txnId.text)
            await post_outputs("May be server got **cked up or you entered wrong number. Send Start to generate OTP again")
            
    except Exception as e:
        await post_outputs(str(e))  
                
async def validate_OTP(OTP, base_request_header):
    if OTP:
        data = {"otp": sha256(str(OTP).encode('utf-8')).hexdigest(), "txnId": txnId}
        await post_outputs("Validating OTP..")
        token = requests.post(url='https://cdn-api.co-vin.in/api/v2/auth/validateMobileOtp', json=data,
                              headers=base_request_header)
        if token.status_code == 200:
            token = token.json()['token']
            await post_outputs('Token Generated')
            global request_header
            request_header = copy.deepcopy(base_request_header)
            request_header["Authorization"] = f"Bearer {token}"
            await slot_finder()
    
        else:
            await post_outputs('Unable to Validate OTP')
            await post_outputs(f"Response: {token.text}")
            await post_outputs("Opps.. Retry OTP entry or Send Start to begin")
        
async def run_script():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', help='Pass token directly')
    args = parser.parse_args()
    global mobile
    mobile = getenv("mobile_number")
    await post_outputs('Running Script')
    
    try:
        global base_request_header
        base_request_header = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
        }
        
        if args.token:
            token = args.token
        else:
            token = await generate_token_OTP(mobile, base_request_header)
        
    except Exception as e:
        await post_outputs(str(e))
    

@client.event
async def on_ready():
  print("We have logged in as {0.user}".format(client))

@client.event
async def on_message(message):
  if message.author == client.user:
    return
  
  if message.content == "Help":
      author = message.author
      await post_outputs(f"To know latest vaccine slot availbility status, send \"Slots\" Private {author}")
      
  if message.content == "Start":
      if str(message.author) == "SaarapPaambu#0534":
          author = message.author
          await message.channel.send(f"On your command, Chief {author}")
          await run_script()

  if message.content == "Slots":
      await post_outputs(last_status)
      
  try:
    if message.content not in ["Help","Start","Slots"]:
        if str(message.author) == "SaarapPaambu#0534":
            if len(str(message.content)) == 6 and isinstance(int(message.content), int):
                OTP = int(message.content)
                print(message.author)
                await validate_OTP(OTP, base_request_header)
            else:
                await message.channel.send("Enter 6-digit OTP. You have eyes, right?")
  except Exception as e:
        await post_outputs(e)

def initiate_client():
    client_token = getenv("client_token")
    client.run(client_token)
    return


nest_asyncio.apply()
initiate_client()


