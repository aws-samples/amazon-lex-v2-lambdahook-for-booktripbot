"""
 Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 SPDX-License-Identifier: MIT-0
 
 Permission is hereby granted, free of charge, to any person obtaining a copy of this
 software and associated documentation files (the "Software"), to deal in the Software
 without restriction, including without limitation the rights to use, copy, modify,
 merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 permit persons to whom the Software is furnished to do so.
 
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

"""
This sample demonstrates an implementation of the Lex Code Hook Interface
in order to serve a sample bot which manages reservations for hotel rooms and car rentals.
Bot, Intent, and Slot models which are compatible with this sample can be found in the Lex Console
as part of the 'BookTrip' template.
This sample is compatible with the Amazon Lex V2 data structure. It can be invoked as a Lambda Hook
at the Fulfillment section of both intents included in the bot configuration (BookHotel and BookCar), 
as well as an initialization and validation function at each turn of the dialog.   
For instructions on how to set up and test this bot, as well as additional samples,
visit the Lex Getting Started documentation http://docs.aws.amazon.com/lex/latest/dg/getting-started.html.
"""

import json
import datetime
import time
import os
import dateutil.parser
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


# --- Helpers that build all of the responses ---


def elicit_slot(session_attributes, active_contexts, intent, slot_to_elicit, message):
    return {
        'sessionState': {
            'activeContexts':[{
                'name': 'intentContext',
                'contextAttributes': active_contexts,
                'timeToLive': {
                    'timeToLiveInSeconds': 600,
                    'turnsToLive': 1
                }
            }],
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'ElicitSlot',
                'slotToElicit': slot_to_elicit
            },
            'intent': intent,
        }
    }


def confirm_intent(active_contexts, session_attributes, intent, message):
    return {
        'sessionState': {
            'activeContexts': [active_contexts],
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'ConfirmIntent'
            },
            'intent': intent
        }
    }


def close(session_attributes, active_contexts, fulfillment_state, intent, message):
    response = {
        'sessionState': {
            'activeContexts':[{
                'name': 'intentContext',
                'contextAttributes': active_contexts,
                'timeToLive': {
                    'timeToLiveInSeconds': 600,
                    'turnsToLive': 1
                }
            }],
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close',
            },
            'intent': intent,
        },
        'messages': [{'contentType': 'PlainText', 'content': message}]
    }

    return response


def delegate(session_attributes, active_contexts, intent, message):
    return {
        'sessionState': {
            'activeContexts':[{
                'name': 'intentContext',
                'contextAttributes': active_contexts,
                'timeToLive': {
                    'timeToLiveInSeconds': 600,
                    'turnsToLive': 1
                }
            }],
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Delegate',
            },
            'intent': intent,
        },
        'messages': [{'contentType': 'PlainText', 'content': message}]
    }


def initial_message(intent_name):
    response = {
            'sessionState': {
                'dialogAction': {
                    'type': 'ElicitSlot',
                    'slotToElicit': 'Location' if intent_name=='BookHotel' else 'PickUpCity'
                },
                'intent': {
                    'confirmationState': 'None',
                    'name': intent_name,
                    'state': 'InProgress'
                }
            }
    }
    
    return response

# --- Helper Functions ---


def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n


def try_ex(value):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary of the Slots section in the payloads.
    Note that this function would have negative impact on performance.
    """

    if value is not None:
        return value['value']['interpretedValue']
    else:
        return None


def generate_car_price(location, days, age, car_type):
    """
    Generates a number within a reasonable range that might be expected for a flight.
    The price is fixed for a given pair of locations.
    """

    car_types = ['economy', 'standard', 'midsize', 'full size', 'minivan', 'luxury']
    base_location_cost = 0
    for i in range(len(location)):
        base_location_cost += ord(location.lower()[i]) - 97

    age_multiplier = 1.10 if age < 25 else 1
    # Select economy is car_type is not found
    if car_type not in car_types:
        car_type = car_types[0]

    return days * ((100 + base_location_cost) + ((car_types.index(car_type.lower()) * 50) * age_multiplier))


def generate_hotel_price(location, nights, room_type):
    """
    Generates a number within a reasonable range that might be expected for a hotel.
    The price is fixed for a pair of location and roomType.
    """

    room_types = ['queen', 'king', 'deluxe']
    cost_of_living = 0
    for i in range(len(location)):
        cost_of_living += ord(location.lower()[i]) - 97

    return nights * (100 + cost_of_living + (100 + room_types.index(room_type.lower())))


def isvalid_car_type(car_type):
    car_types = ['economy', 'standard', 'midsize', 'full size', 'minivan', 'luxury', 'economico', 'mediano', 'lujo']
    return car_type.lower() in car_types


def isvalid_city(city):
    valid_cities = ['nueva york', 'los angeles', 'chicago', 'houston', 'philadelphia', 'phoenix', 'san antonio',
                    'san diego', 'dallas', 'san jose', 'austin', 'jacksonville', 'san francisco', 'indianapolis',
                    'columbus', 'fort worth', 'charlotte', 'detroit', 'el paso', 'seattle', 'denver', 'washington dc',
                    'memphis', 'boston', 'nashville', 'baltimore', 'portland']
    return city.lower() in valid_cities


def isvalid_room_type(room_type):
    room_types = ['queen', 'king', 'deluxe']
    return room_type.lower() in room_types


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def get_day_difference(later_date, earlier_date):
    later_datetime = dateutil.parser.parse(later_date).date()
    earlier_datetime = dateutil.parser.parse(earlier_date).date()
    return abs(later_datetime - earlier_datetime).days


def add_days(date, number_of_days):
    new_date = dateutil.parser.parse(date).date()
    new_date += datetime.timedelta(days=number_of_days)
    return new_date.strftime('%Y-%m-%d')


def build_validation_result(isvalid, violated_slot, message_content):
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': message_content
        #'message': {'contentType': 'PlainText', 'content': message_content}
    }


def validate_book_car(slots):
    pickup_city = try_ex(slots['PickUpCity'])
    pickup_date = try_ex(slots['PickUpDate'])
    return_date = try_ex(slots['ReturnDate'])
    driver_age = safe_int(try_ex(slots['DriverAge']))
    car_type = try_ex(slots['CarType'])

    if pickup_city and not isvalid_city(pickup_city):
        return build_validation_result(
            False,
            'PickUpCity',
            'We currently do not support {} as a valid destination.  Can you try a different city?'.format(pickup_city)
        )

    if pickup_date:
        if not isvalid_date(pickup_date):
            return build_validation_result(False, 'PickUpDate', 'I did not understand your departure date.  When would you like to pick up your car rental?')
        if datetime.datetime.strptime(pickup_date, '%Y-%m-%d').date() <= datetime.date.today():
            return build_validation_result(False, 'PickUpDate', 'Reservations must be scheduled at least one day in advance.  Can you try a different date?')
    else:
        return build_validation_result(
            False,
            'PickUpDate',
            'Elicit PickUpDate'
        )

    if return_date:
        if not isvalid_date(return_date):
            return build_validation_result(False, 'ReturnDate', 'I did not understand your return date.  When would you like to return your car rental?')
    else:
        return build_validation_result(
            False,
            'ReturnDate',
            'Elicit ReturnDate'
        )

    if pickup_date and return_date:
        if dateutil.parser.parse(pickup_date) >= dateutil.parser.parse(return_date):
            return build_validation_result(False, 'ReturnDate', 'Your return date must be after your pick up date.  Can you try a different return date?')

        if get_day_difference(pickup_date, return_date) > 30:
            return build_validation_result(False, 'ReturnDate', 'You can reserve a car for up to thirty days.  Can you try a different return date?')

    if driver_age is not None:
        if driver_age < 18:
            return build_validation_result(
                False,
                'DriverAge',
                'Your driver must be at least eighteen to rent a car.  Can you provide the age of a different driver?'
            )
    else:
        return build_validation_result(
            False,
            'DriverAge',
            'Elicit DriverAge'
        )

    if car_type:
        if not isvalid_car_type(car_type):
            return build_validation_result(
                False,
                'CarType',
                'I did not recognize that model.  What type of car would you like to rent?  '
                'Popular cars are economy, midsize, or luxury')
    else:
        return build_validation_result(
            False,
            'CarType',
            'Elicit CarType'
        )

    return {'isValid': True}


def validate_hotel(slots):
    location = try_ex(slots['Location'])
    checkin_date = try_ex(slots['CheckInDate'])
    nights = safe_int(try_ex(slots['Nights']))
    room_type = try_ex(slots['RoomType'])

    if location is not None and not isvalid_city(location):
        return build_validation_result(
            False,
            'Location',
            'We currently do not support {} as a valid destination.  Can you try a different city?'.format(location)
        )

    if checkin_date is not None:
        if not isvalid_date(checkin_date):
            return build_validation_result(False, 'CheckInDate', 'I did not understand your check in date.  When would you like to check in?')
        if datetime.datetime.strptime(checkin_date, '%Y-%m-%d').date() <= datetime.date.today():
            return build_validation_result(False, 'CheckInDate', 'Reservations must be scheduled at least one day in advance.  Can you try a different date?')
    else:
        return build_validation_result(
            False,
            'CheckInDate',
            'Elicit CheckInDate'
        )
    
    if nights is not None:
        if (nights < 1 or nights > 30):
            return build_validation_result(
                False,
                'Nights',
                'You can make a reservations from one to thirty nights.  How many nights would you like to stay for?'
            )
    else:
        return build_validation_result(
            False,
            'Nights',
            'Elicit Nights'
        )

    if room_type is not None:
        if not isvalid_room_type(room_type):
            return build_validation_result(False, 'RoomType', 'I did not recognize that room type.  Would you like to stay in a queen, king, or deluxe room?')
    else:
        return build_validation_result(
            False,
            'RoomType',
            'Elicit RoomType'
        )
        
    return {'isValid': True}


""" --- Functions that control the bot's behavior --- """


def book_hotel(intent_request):
    """
    Performs dialog management and fulfillment for booking a hotel.
    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """

    intent = intent_request['sessionState']['intent']
    
    session_attributes = {}
    session_attributes['sessionId'] = intent_request['sessionId']
    
    active_contexts = {}
    
    confirmation_status = intent_request['sessionState']['intent']['confirmationState']

    # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
    validation_result = validate_hotel(intent_request['sessionState']['intent']['slots'])
    if not validation_result['isValid']:
        slots = intent_request['sessionState']['intent']['slots']
        slots[validation_result['violatedSlot']] = None

        return elicit_slot(
            session_attributes,
            active_contexts,
            intent_request['sessionState']['intent'],
            validation_result['violatedSlot'],
            validation_result['message']
        )

    # Otherwise, let native DM rules determine how to elicit for slots and prompt for confirmation.  Pass price
    # back in sessionAttributes once it can be calculated; otherwise clear any setting from sessionAttributes.
    else:
        location = try_ex(intent_request['sessionState']['intent']['slots']['Location'])
        checkin_date = try_ex(intent_request['sessionState']['intent']['slots']['CheckInDate'])
        nights = safe_int(try_ex(intent_request['sessionState']['intent']['slots']['Nights']))
        room_type = try_ex(intent_request['sessionState']['intent']['slots']['RoomType'])
        
        if location and checkin_date and nights and room_type:
            # Load confirmation history and track the current reservation.
            reservation = json.dumps({
                'ReservationType': 'Hotel',
                'Location': location,
                'RoomType': room_type,
                'CheckInDate': checkin_date,
                'Nights': nights
            })
            
            active_contexts['ReservationType'] = 'Hotel'
            active_contexts['Location'] = location
            active_contexts['RoomType'] = room_type
            active_contexts['CheckInDate'] = checkin_date
            active_contexts['Nights'] = nights
            # The price of the hotel has yet to be confirmed.
            price = generate_hotel_price(location, nights, room_type)
            session_attributes['currentReservationPrice'] = price
        
            if confirmation_status == 'None':
                return delegate(session_attributes, active_contexts, intent, 'Confirm hotel reservation')

            elif confirmation_status == 'Confirmed':
                # Booking the hotel.  In a real application, this would likely involve a call to a backend service.
                logger.debug('bookHotel under={}'.format(reservation))
                intent['confirmationState']="Confirmed"
                intent['state']="Fulfilled"
                return close(session_attributes, active_contexts, 'Fulfilled', intent,
                    'Tu reservación de hotel ha quedado registrada. ¿Te puedo ayudar con algo más?'
                    #'Thanks, I have placed your reservation.   Please let me know if you would like to book a car, rental, or another hotel.'
                )

   

def book_car(intent_request):
    """
    Performs dialog management and fulfillment for booking a car.
    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """
    logger.debug('bookCar intent')
    slots = intent_request['sessionState']['intent']['slots']
    pickup_city = try_ex(slots['PickUpCity'])
    pickup_date = try_ex(slots['PickUpDate'])
    return_date = try_ex(slots['ReturnDate'])
    driver_age = try_ex(slots['DriverAge'])
    car_type = try_ex(slots['CarType'])
    confirmation_status = intent_request['sessionState']['intent']['confirmationState']
    session_attributes = intent_request['sessionState'].get("sessionAttributes") or {}
    intent = intent_request['sessionState']['intent']
    active_contexts = {}

    logger.debug(confirmation_status)
    # Load confirmation history and track the current reservation.
    reservation = {
        'ReservationType': 'Car',
        'PickUpCity': pickup_city,
        'PickUpDate': pickup_date,
        'ReturnDate': return_date,
        'DriverAge': driver_age,
        'CarType': car_type
    }
    
    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        logger.debug('calling validate_book_car')
        validation_result = validate_book_car(intent_request['sessionState']['intent']['slots'])
        if not validation_result['isValid']:
            if validation_result['violatedSlot'] == 'DriverAge' and confirmation_status == 'Denied':
                validation_result['violatedSlot'] = 'PickUpCity'
                intent['slots'] = {}
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                session_attributes,
                active_contexts,
                intent,
                validation_result['violatedSlot'],
                validation_result['message']
            )  

    if pickup_city and pickup_date and return_date and driver_age and car_type:
        # Generate the price of the car in case it is necessary for future steps.
        price = generate_car_price(pickup_city, get_day_difference(pickup_date, return_date), safe_int(driver_age), car_type)
        session_attributes['currentReservationPrice'] = price
        # Determine if the intent (and current slot settings) has been denied.  The messaging will be different
        # if the user is denying a reservation he initiated or an auto-populated suggestion.
        if confirmation_status == 'Denied':
            logger.debug('Conf status Denied')

            return delegate(session_attributes, active_contexts, intent, 'Confirm hotel reservation')

        if confirmation_status == 'None':
            return delegate(session_attributes, active_contexts, intent, 'Confirm hotel reservation')
            
        if confirmation_status == 'Confirmed':
            intent['confirmationState']="Confirmed"
            intent['state']="Fulfilled"
            return close(
                session_attributes,
                active_contexts,
                'Fulfilled',
                intent,
                'Listo, tu reservación está completa. Ha sido un placer ayudarte. :D'
                #'Thanks, I have placed your reservation.'
            )


# --- Intents ---


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """
    logger.debug(intent_request)
    
    
    slots = intent_request['sessionState']['intent']['slots']
    
    location = slots['Location'] if 'Location' in slots else None
    pickup_city = slots['PickUpCity'] if 'PickUpCity' in slots else None
    
    intent_name = intent_request['sessionState']['intent']['name']
    
    
    #Ignoring initial invocation, which happens after the first interaction of the end user with the intents in the testing interface
    if not isinstance(location, type(None)) or  not isinstance(pickup_city, type(None)):
        logger.debug('dispatch sessionId={}, intentName={}'.format(intent_request['sessionId'], intent_request['sessionState']['intent']['name']))


        # Dispatch to your bot's intent handlers
        if intent_name == 'BookHotel':
            return book_hotel(intent_request)
        elif intent_name == 'BookCar':
            return book_car(intent_request)

        raise Exception('Intent with name ' + intent_name + ' not supported')
        
    #If the user is asking to reserve a car, and there are active session attributes from the BookHotel intent, 
    #Lex will try to confirm if the values should be reused
    elif 'activeContexts' in intent_request['sessionState'] and len(intent_request['sessionState']['activeContexts']):
        active_contexts = intent_request['sessionState']['activeContexts'][0]
        session_attributes = intent_request['sessionState']['sessionAttributes']
        intent = intent_request['sessionState']['intent']
        message = 'Indicame si la reservacion de auto es para {PickUpCity}, empezando {PickUpDate} y terminando {ReturnDate}'
        
        logger.debug(message)
        
        checkin_date = active_contexts['contextAttributes']['CheckInDate']
        return_date = add_days(checkin_date, safe_int(active_contexts['contextAttributes']['Nights']))
        #return_date = checkin_date + datetime.timedelta(days=safe_int(active_contexts['contextAttributes']['Nights']))
        active_contexts['timeToLive']['turnsToLive']=20
        
        logger.debug(return_date)
        
        slots = {
                'PickUpCity': {
                    'shape': 'Scalar', 
                    'value': {
                        'interpretedValue': active_contexts['contextAttributes']['Location'],
                        'originalValue': active_contexts['contextAttributes']['Location'],
                        'resolvedValues': [
                            active_contexts['contextAttributes']['Location']
                        ]
                    }
                },
                'PickUpDate': {
                    'shape': 'Scalar',
                    'value': {
                        'interpretedValue': checkin_date,
                        'originalValue': checkin_date,
                        'resolvedValues': [
                            checkin_date
                        ]
                    }
                },
                'ReturnDate': {
                    'shape': 'Scalar',
                    'value': {
                        'interpretedValue': return_date,
                        'originalValue': return_date,
                        'resolvedValues': [
                            return_date
                        ]
                    }
                }
                #, 
                #'DriverAge': None, 
                #'CarType': None
            }
            
        intent['slots'] = slots
        
        logger.debug('Confirm with context values')
                
        return confirm_intent(active_contexts, session_attributes, intent, message)

    
    logger.debug('Conversation initiated')
    
        
    return initial_message(intent_name)


# --- Main handler ---


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    #logger.debug('event.bot.name={}'.format(event['bot']['name']))
    return dispatch(event)
