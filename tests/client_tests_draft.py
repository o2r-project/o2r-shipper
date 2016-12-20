import requests


def test_post(my_shipment_id, my_compendium_id, my_recipient, my_cookie):
    new_data = {'_id': my_shipment_id, 'compendium_id': str(my_compendium_id), 'recipient': str(my_recipient), 'cookie': str(my_cookie)}
    r = requests.post(''.join((host, 'shipment')), data=new_data)
    print(r.status_code)
    print(r.text)


def test_get(my_id):
    if not my_id:
        # list all
        r = requests.get(''.join((host, 'shipment')))
    else:
        # output specific
        r = requests.get(''.join((host, 'shipment/', my_id)))
    print(r.status_code)
    print(r.text)


# main:
print('client test for o2r shipper service')

host = 'muncher'
zenodo_host = 'https://sandbox.zenodo.org/api'
mongodb_host = 'mongodb://localhost:27017/'
userlevel = 200
the_cookie = ''

try:
    # Shipment create new
    test_post(None, '12345', 'zenodo', the_cookie)

    # Shipment list them all
    test_get(None)

    # Shipment info retrieval based on id
    #test_get('49b878c6-301f-4b98-9f47-e9bef1b8f3b7')
except:
    raise
