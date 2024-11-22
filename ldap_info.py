import logging
import os
import ssl
from dotenv import load_dotenv
from ldap3 import Server, Connection, ALL, Tls

load_dotenv()

# Logger
logging.root.setLevel(os.environ.get('LOGLEVEL', 'INFO').upper())

ldap_server = os.environ['LDAP_SERVER']
ldap_port = int(os.environ['LDAP_PORT'])
ldap_base_dn = os.environ['LDAP_BASE_DN']
ldap_search_filter = os.environ['LDAP_SEARCH_FILTER']
ldap_ciphers = os.environ['LDAP_CIPHERS']
faculty_attribute = os.environ.get('LDAP_FACULTY_ATTRIBUTE', 'faculty')


def connect_anonymous():
    """
    Establish an unauthenticated LDAP connection.
    """
    tls = Tls(ciphers=ldap_ciphers, validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLS)
    server = Server(ldap_server, port=ldap_port, use_ssl=True, tls=tls, get_info=ALL)
    return Connection(server, auto_bind=True)


def retrieve_faculty_info():
    """
    Retrieve faculty information for all users.
    """
    conn = connect_anonymous()

    logging.debug('Searching for user data')
    conn.search(
        ldap_base_dn,
        ldap_search_filter,  # Use a filter that targets the desired results
        attributes=[faculty_attribute]
    )

    faculty_count = {}

    for entry in conn.entries:
        faculty = entry[faculty_attribute].value

        if faculty:
            if faculty in faculty_count:
                faculty_count[faculty] += 1
            else:
                faculty_count[faculty] = 1

    print("Users per Faculty:")
    for faculty, count in faculty_count.items():
        print(f"{faculty}: {count} users")


if __name__ == "__main__":
    retrieve_faculty_info()