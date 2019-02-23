"""Convert Dutch election results in EML format to pandas DataFrames"""

from pathlib import Path, PosixPath
import re
import xmltodict
import pandas as pd


def read_eml(path):

    """Convert EML file to dictionary

    :param path: Path of EML file.
    :return: data from EML file converted to ordered dictionary.
    :rtype: collections.OrderedDict

    """

    try:
        contents = open(path, encoding='utf8', errors='backslashreplace').read()
        return xmltodict.parse(contents)
    except UnicodeDecodeError as e:
        print(path.name)
        print(e)
        return None


def get_id_and_date(source):

    """Get identifier and date of election

    :param pathlib.PosixPath source: Path to folder containing EML files
    :return: tuple containing the identifier and date of the election
    :rtype: tuple

    """

    paths = source.glob('**/Verkiezingsdefinitie*.xml')
    for path in paths:

        data = read_eml(path)
        election = (data['EML']
                        ['ElectionEvent']
                        ['Election'])
        identifier = election['ElectionIdentifier']['@Id']
        date = election['ElectionIdentifier']['kr:ElectionDate']
        return (identifier, date)


def extract_postcode(station_name):

    """Try to extract postcode from station name

    :param str station_name: Station name
    :return: station name, postcode or None
    :rtype: tuple

    """

    pattern = r'(.*?)\(postcode\: (.*?)\)'
    try:
        name, postcode = re.findall(pattern, station_name)[0]
    except IndexError:
        name, postcode = station_name, None
    return name.strip(), postcode


def parse_election_data(data, per_candidate):

    """Parse election data

    :param collections.OrderedDict data: Election data
    :return:
        aggregate results, results per candidate,
        contest name and managing authority
    :rtype: tuple

    """

    if pd.isnull(data):
        return []
    rows_aggregates = []
    rows_per_candidate = []
    election = data['EML']['Count']['Election']
    election_identifier = election['ElectionIdentifier']
    election_id = election_identifier['@Id']
    election_name = election_identifier['ElectionName']
    try:
        election_domain = election_identifier['kr:ElectionDomain']
    except KeyError:
        election_domain = None
    if election_domain and isinstance(election_domain, str):
        election_domain_name = election_domain
        election_domain_id = None
    elif election_domain and isinstance(election_domain, dict):
        try:
            election_domain_id = election_domain['@Id']
        except KeyError:
            election_domain_id = None
        try:
            election_domain_name = election_domain['#text']
        except KeyError:
            election_domain_name = None
    else:
        election_domain_name = None
        election_domain_id = None
    election_date = election_identifier['kr:ElectionDate']
    contest = election['Contests']['Contest']
    try:
        contest_name = contest['ContestIdentifier']['ContestName']
    except KeyError:
        contest_name = None
    try:
        managing_authority = (data['EML']
                                  ['ManagingAuthority']
                                  ['AuthorityIdentifier']
                                  ['#text'])
    except KeyError:
        managing_authority = None
    try:
        stations = contest['ReportingUnitVotes']
    except KeyError:
        stations = []
        rows_aggregates = [{
            'election_id': election_id,
            'election_name': election_name,
            'election_domain_id': election_domain_id,
            'election_domain_name': election_domain_name,
            'election_date': election_date,
            'contest_name': contest_name,
            'managing_authority': managing_authority,
            'station_name': None,
            'station_id': None
            }]
    if not isinstance(stations, list):
        stations = [stations]
    for station in stations:
        if isinstance(station, str):
            print(station)
        item = {
            'election_id': election_id,
            'election_name': election_name,
            'election_domain_id': election_domain_id,
            'election_domain_name': election_domain_name,
            'election_date': election_date,
            'contest_name': contest_name,
            'managing_authority': managing_authority
            }
        try:
            item['station_id'] = station['ReportingUnitIdentifier']['@Id']
        except TypeError:
            item['station_id'] = None
        try:
            station_name = station['ReportingUnitIdentifier']['#text']
        except TypeError:
            station_name = None
        station_name, postcode = extract_postcode(station_name)
        item['station_name'] = station_name
        item['postcode'] = postcode
        item['cast'] = station['Cast']
        item['total_counted'] = station['TotalCounted']
        for rejected in station['RejectedVotes']:
            key = rejected['@ReasonCode'].lower()
            key = f'rejected_{key}'
            value = rejected['#text']
            item[key] = value
        if 'UncountedVotes' in station:
            for reason in station['UncountedVotes']:
                key = reason['@ReasonCode'].lower()
                key = f'uncounted_{key}'
                value = reason['#text']
                item[key] = value
        try:
            results = station['Selection']
        except TypeError:
            results = []
        row_aggregate = item.copy()

        for result in results:
            if 'AffiliationIdentifier' in result.keys():
                party_name = result['AffiliationIdentifier']['RegisteredName']
                party_id = result['AffiliationIdentifier']['@Id']
                if pd.isnull(party_name):
                    party_name = party_id
                votes = int(result['ValidVotes'])
                row_aggregate[party_name] = votes
            elif per_candidate:
                keep = [
                    'election_id',
                    'election_name',
                    'election_domain_name',
                    'election_domain_id',
                    'election_date',
                    'contest_name',
                    'managing_authority',
                    'station_id',
                    'station_name',
                    'postcode'
                ]
                row_cand = {k: item[k] for k in keep}
                row_cand['party_name'] = party_name
                row_cand['party_id'] = party_id
                candidate_id = (result['Candidate']
                                      ['CandidateIdentifier']
                                      ['@Id'])
                row_cand['candidate_identifier'] = candidate_id
                row_cand['votes'] = result['ValidVotes']
                rows_per_candidate.append(row_cand)
        rows_aggregates.append(row_aggregate)
    return (rows_aggregates, rows_per_candidate, contest_name, managing_authority)


def process_files(source, per_candidate):

    """Process data files with local election results

    :param pathlib.PosixPath source: Location of EML files
    :param bool per_candidate: If True, also parse results per candidate
    :return: dictionary of pandas DataFrames containing results per municipality
    :rtype: dict

    """

    paths = source.glob('**/Telling*_*.xml')
    paths = [p for p in paths if 'kieskring' not in str(p).lower()]
    dfs = {}
    for path in paths:
        name = path.stem
        data = read_eml(path)
        rows_aggregates, rows_per_candidate, _, _ = parse_election_data(data,
                                                                        per_candidate)
        if per_candidate:
            key = '{}_per_candidate'.format(name)
            df = pd.DataFrame(rows_per_candidate)
            dfs[key] = df
        key = '{}_aggregate'.format(name)
        df = pd.DataFrame(rows_aggregates)
        first_cols = [
            'contest_name',
            'managing_authority',
            'election_id',
            'election_name',
            'election_domain_id',
            'election_domain_name',
            'election_date',
            'station_name',
            'station_id',
            'postcode',
            'cast',
            'total_counted',
            'rejected_blanco',
            'rejected_ongeldig',
            'uncounted_andere verklaring',
            'uncounted_geen verklaring',
            'uncounted_geldige kiezerspassen',
            'uncounted_geldige stempassen',
            'uncounted_geldige volmachtbewijzen',
            'uncounted_kwijtgeraakte stembiljetten',
            'uncounted_meegenomen stembiljetten',
            'uncounted_meer getelde stembiljetten',
            'uncounted_minder getelde stembiljetten',
            'uncounted_te veel uitgereikte stembiljetten',
            'uncounted_te weinig uitgereikte stembiljetten',
            'uncounted_toegelaten kiezers'
            ]
        first_cols = [c for c in first_cols if c in df.columns]
        columns = first_cols + [c for c in df.columns if c not in first_cols]
        dfs[key] = df[columns]
    return dfs


def parse_candidates(data, rows):

    """Get candidate details

    :param collections.OrderedDict data: Election data
    :param list rows: Result from parsing previous data
    :return: list of rows with additional data added
    :rtype: list

    """

    issue_date = data['EML']['IssueDate']
    election = (data['EML']
                    ['CandidateList']
                    ['Election'])
    election_identifier = election['ElectionIdentifier']
    election_id = election_identifier['@Id']
    election_name = election_identifier['ElectionName']
    try:
        election_date = election_identifier['ns6:ElectionDate']
    except KeyError:
        election_date = election_identifier['kr:ElectionDate']
    try:
        nomination_date = election_identifier['ns6:NominationDate']
    except KeyError:
        nomination_date = election_identifier['kr:NominationDate']
    try:
        election_domain_id = election_identifier['ns6:ElectionDomain']['@Id']
    except KeyError:
        election_domain_id = election_identifier['kr:ElectionDomain']['@Id']
    try:
        election_domain_name = election_identifier['ns6:ElectionDomain']['#text']
    except KeyError:
        election_domain_name = election_identifier['kr:ElectionDomain']['#text']

    try:
        contest_name = (election['Contest']
                                ['ContestIdentifier']
                                ['ContestName'])
    except KeyError:
        contest_name = None
    try:
        election_name = election['ElectionIdentifier']['ElectionName']
    except KeyError:
        election_name = None
    parties = election['Contest']['Affiliation']
    for party in parties:
        party_name = party['AffiliationIdentifier']['RegisteredName']
        party_id = party['AffiliationIdentifier']['@Id']
        party_candidates = party['Candidate']
        for candidate in party_candidates:
            try:
                identifier = candidate['CandidateIdentifier']['@Id']
            except TypeError:
                identifier = None
            if not isinstance(candidate, dict):
                continue
            for key in candidate['CandidateFullName'].keys():
                if key.startswith('ns'):
                    nr = key[2]
                    break
            try:
                first_name = (candidate['CandidateFullName']
                                       ['ns{}:PersonName'.format(nr)]
                                       ['ns{}:FirstName'.format(nr)])
            except (TypeError, KeyError):
                first_name = None
            try:
                last_name = (candidate['CandidateFullName']
                                      ['ns{}:PersonName'.format(nr)]
                                      ['ns{}:LastName'.format(nr)])
            except TypeError:
                last_name = None
            try:
                initials = (candidate['CandidateFullName']
                                     ['ns{}:PersonName'.format(nr)]
                                     ['ns{}:NameLine'.format(nr)]
                                     ['#text'])
            except TypeError:
                initials = None
            try:
                prefix = (candidate['CandidateFullName']
                                   ['ns{}:PersonName'.format(nr)]
                                   ['ns{}:NamePrefix'.format(nr)])
            except (TypeError, KeyError):
                prefix = None
            try:
                gender = candidate['Gender']
            except (TypeError, KeyError):
                gender = None

            try:
                address = (candidate['QualifyingAddress']
                                    ['ns{}:Locality'.format(nr)]
                                    ['ns{}:LocalityName'.format(nr)])
            except (TypeError, KeyError):
                address = None
            rows.append({
                'election_identifier': election_identifier,
                'election_id': election_id,
                'election_name': election_name,
                'election_date': election_date,
                'nomination_date': nomination_date,
                'election_domain_id': election_domain_id,
                'election_domain_name': election_domain_name,
                'contest_name': contest_name,
                'election_name': election_name,
                'party_name': party_name,
                'party_id': party_id,
                'candidate_identifier': identifier,
                'first_name': first_name,
                'last_name': last_name,
                'initials': initials,
                'prefix': prefix,
                'gender': gender,
                'address': address
            })

    return rows


def create_candidate_list(source):

    """Create list with candidate details

    :param pathlib.PosixPath source: Location of EML files
    :return: pandas Dataframe containing the candidates

    """

    rows = []
    paths = source.glob('**/Kandidatenlijsten_*.xml')
    for path in paths:
        data = read_eml(path)
        if pd.notnull(data):
            rows = parse_candidates(data, rows)
    return pd.DataFrame(rows)


def parse_eml(source, per_candidate=False):

    """Parse EML

    :param pathlib.PosixPath source: Path to folder containing EML files
    :param bool per_candidate: If true, also get results per candidate
    :return: dictionary of pandas DataFrames containing results per municipality
    :rtype: dict

    """

    if not isinstance(source, PosixPath):
        source = Path(source)
    dfs = process_files(source, per_candidate)
    if per_candidate:
        dfs['candidate_list'] = create_candidate_list(source)
    return dfs
