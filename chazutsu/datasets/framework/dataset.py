import os
import re
from random import random
import zipfile
import tarfile
import requests
from tqdm import tqdm


class Dataset():
    """ Dataset Class Framework """

    def __init__(self, name, site_url, download_url, description, log_level=None):
        """
        Args:
            name        : dataset name
            site_url    : url to access the dataset homepage
            download_url    : dataset download url
            description     : description of dataset
        """

        self.name = name
        self.site_url = site_url
        self.download_url = download_url
        self.description = description

        # create logger
        from logging import getLogger, StreamHandler, DEBUG
        self.logger = getLogger("_".join(["dataset", self.__class__.__name__.lower()]))
        if not self.logger.hasHandlers():
            # logger is global object!
            _level = DEBUG if log_level is None else log_level
            handler = StreamHandler()
            handler.setLevel(_level)
            self.logger.setLevel(_level)
            self.logger.addHandler(handler)
    
    def download(self, directory, test_size=0.3, sample_size=0, keep_raw=False):
        # input parameter check
        #   directory: don't make default directory in download method because can not specify current dir.
        #   test_size: have to be smaller than 1
        self.check_directory(directory)
        dataset_root = os.path.join(directory, self.name)
        
        # download and save file
        save_file_path = self.save_dataset(dataset_root)

        # extract dataset file from saved file
        extracted_file_path = self.extract(save_file_path)

        # split to train & test
        self.train_test_split(extracted_file_path, test_size)
    
        # make sample file
        self.make_samples(save_file_path, sample_size)
        
        # remove raw file
        if not keep_raw:
            os.remove(extracted_file_path)
        
        self.logger.info("Done all process!")
    
    def save_dataset(self, dataset_root):
        # download and save it as raw file
        self.logger.info("Begin downloading the {} dataset from {}.".format(self.name, self.download_url))
        resp = requests.get(self.download_url, stream=True)
        if not resp.ok:
            raise Exception("Can not get dataset from {}.".format(self.download_url))
        
        # save content in response to file
        total_size = int(resp.headers.get("content-length", 0))
        file_name = self._get_file_name(resp)
        _, ext = os.path.splitext(file_name)
        save_file_path = os.path.abspath(os.path.join(dataset_root, file_name))
        self.logger.info("The dataset file is saved to {}".format(save_file_path))
        with open(save_file_path, "wb") as f:
            chunk_size = 1024
            limit = total_size / chunk_size
            for data in tqdm(resp.iter_content(chunk_size=chunk_size), total=limit, unit="B", unit_scale=True):
                f.write(data)
        
        return save_file_path
    
    def extract(self, path):
        # you may unpack the file and extract data file.
        return path
    
    def extract_file(self, path, relative_paths, remove=True):
        # unpack the archive file and extract directed path file
        base, _ = os.path.splitext(path)
        root = os.path.basename(path).split(".")[0] + "/"
        target = relative_paths if isinstance(relative_paths, (tuple, list)) else [relative_paths]

        extracteds = []
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as z:
                for n in map(lambda n: n.replace(root, ""), z.namelist()):
                    if n in target:
                        file_name = os.path.basename(n)
                        p = os.path.join(os.path.dirname(path), file_name)
                        with open(p, "wb") as f:
                            f.write(z.read(root + n))
                        extracteds.append(p)

        elif tarfile.is_tarfile(path):
            with tarfile.open(path) as t:
                for m in map(lambda m: m.replace(root, ""), t.getnames()):
                    if m in target:
                        file_name = os.path.basename(m)
                        p = os.path.join(os.path.dirname(path), file_name)
                        with open(p, "wb") as f:
                            with t.extractfile(root + m) as tf:
                                for c in tf:
                                    f.write(c)
                        extracteds.append(p)
        
        if remove:
            os.remove(path)

        return extracteds

    def train_test_split(self, original_file_path, test_size):
        if test_size < 0 or test_size > 1:
            self.logger.error("test_size have to be between 0 ~ 1. if you don't want to split, please set 0.")
            return None
        elif test_size == 0 or test_size == 1:
            return None

        self.logger.info("Split to train & test file.")

        total_count = self.get_line_count(original_file_path)
        def is_test():
            r = random.random()
            return True if r <= test_size else False
        
        base, ext = os.path.splitext(original_file_path)
        train_file = open(base + "_train" + ext, "wb")
        test_file = open(base + "_test" + ext, "wb")

        test_count = 0
        with open(original_file_path, "rb") as f:
            for line in tqdm(f, total=total_count):
                target, tc = test_file, 1 if is_test() else train_file, 0
                target.write(line)
                test_count += tc

        train_file.close()
        test_file.close()

        self.logger.info("Splited to {} train & {} test({:.2f}%).".format(
            total_count - test_count, test_count, test_count / total_count * 100)
            )
        return None

    def make_samples(self, original_file_path, sample_size):
        if sample_size == 0:
            return None
        
        self.logger.info("Make sample file.")
        base, ext = os.path.splitext(original_file_path)
        samples_file = open(base + "_samples" + ext, "wb")
        with open(original_file_path, "rb") as f:
            count = 0
            for line in f:
                samples_file.write(line)
                count += 1
                if count > sample_size:
                    break
        sample_file.close()

        return None

    def _get_file_name(self, resp):
        cd = resp.headers["content-disposition"]
        file_matches = re.search("filename=(.+)", cd)
        file_name = ""
        if file_matches:
            file_name = file_matches.group(0)
            file_name = file_name.split("=")[1]

        return file_name

    def get_line_count(file_path):  
        count = 0
        with open(file_path, "r+") as fp:
            buf = mmap.mmap(fp.fileno(), 0)
            while buf.readline():
                count += 1
        return count

    def check_directory(self, directory, make_default_at=""):
        if os.path.isdir(directory):
            return directory
        elif make_default_at:
            data_dir = os.path.join(base_dir, "data")
            os.mkdir(data_dir)
            return data_dir
        else:
            raise Exception("Directed directory {} does not exist.".format(directory))

    def show(self):
        print("About {}".format(self.name))
        print(self.description)
        print("see also: {}".format(self.site_url))

