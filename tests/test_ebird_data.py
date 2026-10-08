import csv
import io
import unittest
import zipfile
from ebird_data import read_export, EbirdIndex, bird_csv, species_key


COLUMNS = ['Submission ID','Common Name','Scientific Name','Taxonomic Order','Date','Count']


def export(rows):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(COLUMNS)
    writer.writerows(rows)
    return ('\ufeff' + stream.getvalue()).encode('utf-8')


class EbirdTests(unittest.TestCase):
    def setUp(self):
        self.content = export([
            ['old','Great Tit','Parus major',1,'2026-08-28',2],
            ['start','Great Tit (Great)','Parus major major',1,'2026-08-29',3],
            ['start','Redpoll (Lesser)','Acanthis flammea cabaret',2,'2026-08-29','X'],
            ['start','hawk sp.','Accipitridae sp. (hawk sp.)',3,'2026-08-29',1],
            ['end','Redpoll','Acanthis flammea',2,'2026-09-05',4],
            ['end','Redpoll','Acanthis flammea',2,'2026-09-05',4],
            ['after','Other','Turdus merula',4,'2026-09-06',1],
        ])
        self.trip = {'name':'Rome','start_date':'2026-08-29','end_date':'2026-09-05','area_label':'Anywhere'}

    def test_inclusive_calendar_dates_no_area_filter_and_prior_history(self):
        data = read_export(self.content)
        summary, birds = EbirdIndex(data).trip(self.trip)
        self.assertEqual(summary['Checklists'],2)
        self.assertEqual(summary['Waarnemingen'],4)
        self.assertEqual(summary['Soorten'],2)
        self.assertEqual(summary['Nieuw voor mij'],1)
        self.assertEqual(summary['Niet op soort'],1)
        redpoll = next(row for row in birds if row['Wetenschappelijke naam']=='Acanthis flammea')
        self.assertEqual(redpoll['Bekend aantal'],4)
        self.assertEqual(redpoll['Aantal onbekend (X)'],1)
        self.assertTrue(redpoll['Nieuw voor mij'])
        self.assertEqual(redpoll['Checklists'],2)
        self.assertEqual(len(data['observations']),6)
        self.assertTrue(bird_csv(birds).startswith(b'\xef\xbb\xbf'))

    def test_zip_and_csv_give_same_result(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            archive.writestr('MyEBirdData.csv', self.content)
        self.assertEqual(read_export(stream.getvalue()),read_export(self.content))

    def test_same_day_trip_and_overlap(self):
        index=EbirdIndex(read_export(self.content))
        summary,_=index.trip({**self.trip,'end_date':'2026-08-29'})
        self.assertEqual(summary['Waarnemingen'],3)
        self.assertEqual(summary['Nieuw voor mij'],1)
        summary,_=index.trip({**self.trip,'start_date':'2027-01-01','end_date':'2027-01-02'})
        self.assertEqual(summary['Soorten'],0)

    def test_taxonomy_groups_and_unidentified(self):
        self.assertEqual(species_key('Parus major [major Group]','Great Tit (Great)'), 'Parus major')
        self.assertEqual(species_key('Acanthis flammea cabaret/rostrata','Redpoll'), 'Acanthis flammea')
        for scientific, common in [('Accipitridae sp.','hawk sp.'),('Anas platyrhynchos x rubripes','hybrid'),('Anas platyrhynchos/rubripes','Mallard/American Black Duck'),('Cairina moschata (Domestic type)','Muscovy Duck (Domestic type)')]:
            self.assertIsNone(species_key(scientific,common))

    def test_bad_inputs_do_not_silently_omit_records(self):
        for content in [b'other,columns\n1,2\n', export([['a','Bird','Parus major',1,'bad','1']]), export([['a','Bird','Parus major',1,'2026-01-01','many']]), export([])]:
            with self.assertRaises(ValueError):
                read_export(content)
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            archive.writestr('a.csv',self.content)
            archive.writestr('b.csv',self.content)
        with self.assertRaises(ValueError):
            read_export(stream.getvalue())


if __name__ == '__main__':
    unittest.main()
