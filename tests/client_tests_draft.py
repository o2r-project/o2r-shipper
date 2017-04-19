import requests


def test_post(my_shipment_id, my_compendium_id, my_recipient, my_cookie):
    new_data = {'_id': my_shipment_id, 'compendium_id': str(my_compendium_id), 'recipient': str(my_recipient), 'cookie': str(my_cookie)}
    r = requests.post(''.join((host, 'shipment')), data=new_data)
    print(r.status_code)
    print(r.text)


def test_post_update(my_depot, my_compendium_id, my_recipient, my_cookie):
    test_md = {'metadata': {
        "creators": [{
            "name": "Tester, Ted",
            "affiliation": "Univ"
        }],
        "publication_date": "2017-02-05",
        "description": "Some words about it.",
        "title": "Just a test title",
        "upload_type": "publication",
        "publication_type": "other",
        "access_right": "open",
        "license": "cc-by"}}
    new_data = {'deposition_id': my_depot, 'compendium_id': str(my_compendium_id), 'recipient': str(my_recipient), 'md': str(test_md), 'cookie': str(my_cookie)}
    r = requests.post(''.join((host, 'shipment')), data=new_data)
    print(r.status_code)
    print(r.text)


def test_return_filelist(my_depot, my_shipment_id, my_compendium_id, my_recipient, my_cookie):
    new_data = {'deposition_id': my_depot, '_id': my_shipment_id, 'compendium_id': str(my_compendium_id), 'recipient': str(my_recipient), 'cookie': str(my_cookie)}
    r = requests.post(''.join((host, 'shipment')), data=new_data)
    print(r.status_code)
    print(r.text)


def test_del(my_shipment_id, my_compendium_id, my_recipient, file_id, my_cookie):
    #new_data = {'_id': my_shipment_id, 'compendium_id': str(my_compendium_id),  'recipient': str(my_recipient), 'cookie': str(my_cookie)}
    r = requests.delete(''.join((host, 'shipment/', my_shipment_id, '/files/', file_id)))
    print(r.status_code)
    print(r.text)


#def test_del_whole_depot(my_depot, my_shipment_id, my_recipient, my_cookie):
#    new_data = {'deposition_id': my_depot, '_id': my_shipment_id, 'recipient': str(my_recipient), 'cookie': str(my_cookie)}
#    r = requests.post(''.join((host, 'shipment')), data=new_data)
#    print(r.status_code)
#    print(r.text)


def test_publishment(my_shipment_id, my_recipient, my_cookie):
    new_data = {'_id': my_shipment_id, 'recipient': str(my_recipient), 'cookie': str(my_cookie)}
    r = requests.put(''.join((host, 'shipment/', my_shipment_id, '/publishment')), data=new_data)
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


if __name__ == "__main__":
    print('client test for o2r shipper service')

    host = 'http://localhost:8087/api/v1/'
    zenodo_host = 'https://sandbox.zenodo.org/api'
    userlevel = 200  # enter user level
    the_cookie = ''  # enter cookie string
    try:
        # Shipment create new
        test_post(None, '4XgD9', 'zenodo', the_cookie)

        # Shipment update metadata only
        #test_post_update('69159', '4XgD9', 'zenodo', the_cookie)

        # Shipment publishment (! insert current shipment id !)
        #test_publishment('19564593-c01f-4e5d-b164-5b7d016e352d', 'zenodo', the_cookie)

        # Shipment list all files from specific depot
        #test_return_filelist('69342', None, '4XgD9', 'zenodo', the_cookie)

        # Shipment delete whole depot (deprecated)
        #test_del_whole_depot('69342', None, 'zenodo', the_cookie)

        # Shipment delete file from specific depot
        #test_del(None, '4XgD9', 'zenodo', '110d667c-7691-4fc9-93e7-5652a52df6f2', the_cookie)

        # Shipment list them all
        #test_get(None)

        # Shipment info retrieval based on id
        #test_get('49b878c6-301f-4b98-9f47-e9bef1b8f3b7')
    except:
        raise
