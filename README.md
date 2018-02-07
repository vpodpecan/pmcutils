## Text extraction from the NCBI OAC article collection

### About
This project implements a Django web application which enables text extraction from the PMC open access document collection (PMC OAC). Although PMC offers `.txt` versions of articles they are not really suitable for text mining because they contain the complete texts including front matter, references, links, etc. thus introducing a lot of noise.

This application works on original XML files and allows for the extraction and deletion of user-specified parts of the XML. For example, it is possible to extract only the body of the text while removing tables, images and links.

The application works on a **local copy** of the PMC OAC document collection which you will have to download from the PMC FTP service. You can use all the `.xml.tar.gz` archive files from the PMC FTP archive: [ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/](ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/).

To obtain the list of article IDs relevant to the query, the application calls the NCBI `esearch` service. Therefore, rate limiting is implemented to respect the limits imposed by NCBI. You are encouraged to obtain a NCBI API key which will increase this limit. Please read [NCBI Insights](https://ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/) for more information.

The application will read the XML data from a database so you will need a high-performance database (Postgres is recommended and used by default). The application also provides a Django management command which will import the contents of an archive into the database.

In lack of a better name the Django project is named `pmcutils` and the search application `oac_search`.


### License

The code is licensed under the MIT license.


### Author

&copy; 2017 [Vid Podpečan](http://kt.ijs.si/vid_podpecan/), [Jožef Stefan Institute](http://kt.ijs.si/) & [National Institute of Biology](http://www.nib.si/eng/index.php/departments/department-of-biotechnology-and-systems-biology)   
Contact: vid.podpecan@ijs.si


### Requirements
1.  Python 3.5+
2.  python packages listed in `requirements.txt`  
3.  Postgres
4.  javascript libraries (included in the source): jquery, js.cookie, loadingOverlay, bootstrap, bootbox, sprintf
5.  Nginx and `uWSGI` (for production)


### Installation

The installation procedure is very similar to the one I wrote for the [brapi-python](https://github.com/vpodpecan/brapi-python) project so you should read that first.


1.  First, you need to install Postgres. Please consult the official documentation how to do that on your system. You will also have to create a user and a database which will be used by the web application.

2.  Create a new Python virtual environment and install the requirements.

3.  Create your `local_settings.py` file and fill in Postgres credentials:
    ```sh
    cd pmcutils
    cp __local_settings.py local_settings.py
    nano local_settings.py
    ```

4.  Activate the new virtual environment and import archive files into the database. For example:
    ```sh
    python manage.py import_archive articles.A-B.xml.tar.gz
    ```
    Now it's a good time to have a nap because the archives are big and import will take some time. To speed up the lenghty process you can import several archives in parallel. Just open another console and repeat the command on another archive.

5.  If you have a NCBI API KEY you can put it in the file `oac_search/api_key.py`:
    ```python
    API_KEY = 'your secret key'
    ```

6.  If you do not need the production-ready installation you can stop here and launch the Django development server
    ```sh
    python manage.py runserver
    ```
    and open the application's main page: [http://127.0.0.1:8000/search](http://127.0.0.1:8000/search)

7.  For a production environment you will have to set up nginx and uwsgi. You can use config templates in the `conf` subdir. See the [brapi-python](https://github.com/vpodpecan/brapi-python) manual for details.


### Updating the database

NCBI daily updates the archives with new articles. The changes are not significant from day to day but the updates accumulate and finally your database will become obsolete. In order to keep your database up-to-date the `import_archive` command can help. By default, it will not overwrite existing database records unless the `--overwrite` option is given. Therefore, in order to update it is enough to download new archives and repeat the import process (see step 6 above).


### Fine tuning

The application fully utilizes system's resources by creating a pool of workers which extract articles in parallel. There is a number of parameters which can be fine tuned to maximize the performance on your machine (see `oac_search/views.py`):

1.  By default, the extraction will occupy all available CPU cores. You will need to reduce that if you want the machine to remain usable during lenghty extractions.

2.  XML documents are submitted to the extraction processes in batches. The default batch size is `min(50, N//cpu_count())` but you may optimize this number to suit your configuration.

3.  The parent process which distributes the load to workers does not put more than 20 batches into each processing queue. You may want to increase or decrease this number to optimize for your memory configuration.
