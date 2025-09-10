import glob
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from lxml import etree

ns = {'tei': 'http://www.tei-c.org/ns/1.0'}


def get_xml_files(idp_data_path: str):
    dclp_files = glob.glob(os.path.join(idp_data_path, 'DCLP', '**', '*.xml'), recursive=True)
    ddb_files = glob.glob(os.path.join(idp_data_path, 'DDB_EpiDoc_XML', '**', '*.xml'), recursive=True)
    all_files = dclp_files + ddb_files
    return dclp_files, ddb_files, all_files


@dataclass
class PapyrusFilter:
    target_files: list[str]
    ddb_collection: str
    dclp_hybrid: str
    title: str
    orig_place: str
    single_match: bool

    def filter_file(self, file):
        title_matches = False
        dclp_hybrid_matches = False
        place_matches = False
        root = etree.parse(file)
        if self.dclp_hybrid:
            if 'DCLP' in file:
                tei_dclp_hybrid = root.xpath('//tei:publicationStmt/tei:idno[@type="dclp-hybrid"]/text()',
                                             namespaces=ns)
                if tei_dclp_hybrid:
                    if self.dclp_hybrid.lower() in tei_dclp_hybrid[0].lower():
                        dclp_hybrid_matches = True
        if self.title:
            tei_title = root.xpath('//tei:titleStmt/tei:title/text()', namespaces=ns)
            if tei_title:
                if self.title.lower() in tei_title[0].lower():
                    title_matches = True
        if self.orig_place:
            tei_place = root.xpath('//tei:origin/tei:origPlace/text()', namespaces=ns)
            if tei_place:
                if self.orig_place.lower() in tei_place[0].lower():
                    place_matches = True
        if self.single_match:
            if title_matches or dclp_hybrid_matches or place_matches:
                return file
        else:
            if self.dclp_hybrid:
                if title_matches and dclp_hybrid_matches and place_matches:
                    return file
            else:
                if title_matches and place_matches:
                    return file
        return None

    def filter(self):
        filtered_files = []
        if self.ddb_collection:
            for file in self.target_files:
                if file.__contains__(os.path.join('DDB_EpiDoc_XML', self.ddb_collection)):
                    filtered_files.append(file)
        else:
            filtered_files = self.target_files
        final_files = []
        if self.dclp_hybrid or self.title or self.orig_place:
            with ThreadPoolExecutor(max_workers=os.cpu_count() + 1) as executor:
                futures = [executor.submit(self.filter_file, file) for file in filtered_files]
                for future in as_completed(futures):
                    if future.result():
                        final_files.append(future.result())
        else:
            final_files = filtered_files
        return final_files
