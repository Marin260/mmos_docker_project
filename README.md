# mmos_docker_project

Uni project. Dockerize existing Django folder

# Django i Docker Compose

U ovom radu bit će objašnjeno kako koristit alat [Docker](https://www.docker.com/ "Službena Docker stranica") i [Docker compose](https://docs.docker.com/compose/ "SLužbena Docker Compose dokumentacija") Za kontejnerizaciju jedne Django aplikacije, koja u ovom slučaju koristi sustav za cacheiranje [Redis](https://redis.io/ "Službena Redis stranica") i bazu podataka [PostgreSQL](https://www.postgresql.org/ "Službena Postgres stranica").

## Django aplikacija

U ovom primjeru koristi se *Blog* aplikacija gdje korisnici mogu stvoriti račun, prijaviti se sa njihovim podacima, stvarati nove objave, uređivati objave, dodati sliku svog profila, izmjeniti lozinku putem maila itd...

### Korištenje PostgreSQL baze podataka

Prije samog podešavanja Djago konfiguracije potrebno je [instalirati PostgreSQL](https://www.postgresql.org/download/linux/ubuntu/ "Upute za instalaciju na Ubuntu") bazu na računalo i stvoriti novu bazu podataka u njoj. Django ima sqlite3 kao zadanu bazu tako da je potrebno instalirati dodatne pakete kako bi mogli koristiti Postgres. Jedan od tih paketa je Postgres adapter za Python porgramski jezik, `psycopg`.
Ako su ispunjeni svi preduvijeti, možemo instalirati `psycopg` kao svaki drugi Python paket koristeći `pip`:

```bash
    $ pip install psycopg2
```

Sada je potrebno izmjeniti postavke u nasem Django projektu. Zadane postavke koje imamo u datoteci `settings.py`:

```py
    # mojProjekt/settings.py
    ...
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': str(BASE_DIR / 'db.sqlite3'),
        }
    }
```

Koristimo sada Postgres predložak i popunimo sa našim podacima

```py
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': '<db_name>',
            'USER': '<db_username>',
            'PASSWORD': '<password>',
            'HOST': '<db_hostname_or_ip>',
            'PORT': '<db_port>',
        }
    }
```

Ako pri instalaciji Postgresa nismo dirali postavke i stvarali nove baze onda predložak možemo popuniti na slijedeći način:

```py
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'postgres',
            'USER': 'postgres',
            'PASSWORD': 'postgres',
            'HOST': 'localhost',
            'PORT': '',
        }
    }
```

Baza postgres već postoji čim instaliramo Postgres, a korisnik i lozinka su isto tako već predefinirani. `HOST` postavimo na `localhost`. Ako nismo dirali postavke, baza je aktivna već postavljen u Postgres postavkama na `5432` tako da to nije potrebno upisati, no u slučaju da promijenimo port u postavkama onda će biti potrebno i navesti u postavkama o kojem se portu radi.
Nakon promjene konfiguracijske datoteke `settings.py` sada možemo migrirati podatke u našu novu bazu.

```bash
    $ ./manage.py makemigrations
```

```bash
    $ ./manage.py migrate
```

!!! Warning
    U fazi razvoja ovi podaci su dovolji za rad na aplikaciji, no u fazi produkcije potrebno ih je izmeniti. Kada budemo radili sa Dockerom ove podatke ćemo izmjeniti.

### Korištenje Redis-a u Django projektu

Django verzija `4.0` osim `Memcached`,`Redis` je sada izvorno podržan tako da nam to znatno olakšava rad što znači ćemo moći pratiti službene upute iz Django dokumentacije kako bi postavili naš sustav. [`Dokumentacija`](https://docs.djangoproject.com/en/4.0/topics/cache/#redis) 
Kao i kod PostgreSQL potrebno je prvo [instalirati redis](https://redis.io/download#installation "Upute za instalaciju") na računalo. Da bi mogli raditi sa Redisom potreban nam je server koji radi na lokalnom ili udaljenom uređaju. U našem primjeru raditi će lokalo. U terminalu pokrečemo server koristeći slijedeću naredbu:

```shell
    $ redis-server
```

Provjerimo sada radi li sve kako treba:

```shell
    $ redis-cli ping
    PONG
```

Vraća nam se odgovor `PONG`, to nam odgovara te idemo dalje u postavke našeg projekta gdje možemo zaljepiti slijedeće `CACHES` postavke:

```py
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379',
        }
    }
```

S obzirom na to da smo Redis server pokrenuli lokalno, postavljena je lokacija na `localhost` na vratima `6379` (*Redisova izvorno zadana vrata*).

!!! Note
    Lokaciju je potrebno izmjeniti u produkcijskom okruženju. Izmjene moraju pratiti zadane redis scheme koje možemo naći u [dokumentaciji](https://redis-py.readthedocs.io/en/stable/#redis.ConnectionPool.from_url).
    Često `Redis` serveri znaju biti zaštićeni sa autentifikacijom te je potrebno ubaciti i korisničko ime i lozinku u `URL`.
    ```py
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.redis.RedisCache',
                'LOCATION': 'redis://username:password@127.0.0.1:6379',
            }
        }
    ```
    Radi jednostavnosti ovaj dio preskačemo.
    Mi ćemo također promijeniti lokaciju kada budemo radili s Docker-om

#### Per-site cache

Najjednostavniji način cacheiranja za našu stranicu, možda nije najbolja opcija, ali za naše potrebe je dovoljno. `Django` dodatno nudi `per-view cahce` koji koristi dekoratore za cacheiranje odredenih pogleda.
Da bi mogli koristiti `per-site cache` moramo promjeniti postavke našeg `MIDDLEWARE`-a u `settings.py`. Dodamo slijedeće linije u postavke:

```py
    MIDDLEWARE = [
        'django.middleware.cache.UpdateCacheMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.cache.FetchFromCacheMiddleware',
    ]
```

!!! warning
    Redosljed kojime upisujemo u postavke je bitan. `UpdateCacheMiddleware` mora biti iznad `CommonMiddleware`, a `FetchFromCacheMiddleware` ispod.

Potrebno je još samo dodati slijedece neophodne postvake u `settings.py`:

* `CACHE_MIDDLEWARE_ALIAS` - alias koji se koristi za pohranu (`default: 'default'`)
* `CACHE_MIDDLEWARE_SECONDS` - vrijeme sekunda koliko će stranica biti spremljena (`default: 31449600`, okvirno 1 godina u sec.)
* `CACHE_MIDDLEWARE_KEY_PREFIX` - ako se predmemorija dijeli na više stranica koristeći istu instancu Django aplikacije, onda je potrebno ovo postaviti na ime stranice ili na neki jednistvani identifikator kako bi se izbijegle kolizije. Puštamo prazno ako nam nije potrebno.
Izmjene koje smo primjenili:

```py
    # mojProjekt/settings.py
    ...
    CACHE_MIDDLEWARE_ALIAS = 'default'
    CACHE_MIDDLEWARE_SECONDS = 600
    CACHE_MIDDLEWARE_KEY_PREFIX = ''
```

## Docker i Docker Compose

Sada možemo krenuti na Docker i Docker compose da bi definirali više kontejnera za našu aplikaciju. Naša aplikacija ovisi o nekim paketima (*engl. dependencies*) koje ćemo morati navesti u naš `Dockerfile` kako bi aplikacija mogla raditi. Imena paketa i njihove verzije ćemo spremiti u datoteku `requirements.txt` za kasniju upotrebu. Da bi dodemo do svih tih paketa možemo koristit sljedeću naredbu:

```shell
    $pip freeze > requirements.txt
```

ako sada ispišemo sadržaj datoteke `requirements.txt` možemo primjetiti da imamo previše paketa, to jest da su se zapisali svi paketi instalirani na našem računalu.

```shell
    $ cat requirements.txt 
    anyio==3.4.0
    apturl==0.5.2
    argon2-cffi==21.3.0
    argon2-cffi-bindings==21.2.0
    asgiref==3.4.1
    astroid==2.3.3
    attrs==19.3.0
    Babel==2.9.1
    backcall==0.1.0
    backports.zoneinfo==0.2.1
    bcrypt==3.1.7
    beautifulsoup4==4.8.2
    bleach==4.1.0
    blinker==1.4
    Brlapi==0.7.0
    cached-property==1.5.1
    certifi==2019.11.28
    cffi==1.15.0
    chardet==3.0.4
    chrome-gnome-shell==0.0.0
    Click==7.0
    colorama==0.4.3
    command-not-found==0.3
    core==6.5.0
    cryptography==2.8
    cupshelpers==1.0
    cycler==0.11.0
    dbus-python==1.2.16
    decorator==4.4.2
    defer==1.0.6
    defusedxml==0.7.1
    distro==1.4.0
    distro-info===0.23ubuntu1
    Django==4.0.1
    django-crispy-forms==1.13.0
    docker==4.1.0
    docker-compose==1.25.0
    dockerpty==0.4.1
    docopt==0.6.2
    duplicity==0.8.12.0
    entrypoints==0.3
    fabric==2.5.0
    factory-boy==3.2.1
    Faker==9.9.0
    fasteners==0.14.1
    fonttools==4.28.4
    future==0.18.2
    grpcio==1.16.1
    grpcio-tools==1.14.1
    gunicorn==20.1.0
    ...
```

da bi dosli do nama potrebnih datoteka trebmo prvo napraviti virtualno okruženje (*engl. virtual environment*) ili bolje poznato kao u Pythonu `venv`. `venv` je alat koji nam pomaže da odvojimo pakete o kojima ovisi jedan projekt od paketa koji nam trebaju u drugom projektu. Da bi stvorili novo virtualno okruženje, prvo se smjestimo u novi prazan direktoriji u koji ćemo postaviti naš projekt, zatim koristimo sljedeću naredbu za stvaranje `venv`:

```shell
    $ python3 -m venv my-project-env
```

Naredba iznad stvara direktoriji imena `my-project-env` koji sadrži kopiju od `Python binary`, `pip` upravitelj paketa, standardnu Python biblioteku i druge prateće datoteke.
Da bi pokrenuli virtualno okruženje moramo ga aktivirati sa `activate` skriptom:

```shell
    $ source my-project-env/bin/activate
```

primimjetimo kako se i prompt pomjenio nakon aktivacije

```shell
    (my-project-env) $
```

Sada možemo svrstati u naš projekt u isti folder gdje se nalazi naše virtualno okruženje i instalirati sve potrebne pakete potrebne za rad aplikacije.

!!! Note
    Virtualno okruženje je praktičnije napraviti prije početka samog rada na aplikaciji no u ovom slučaju imamo već gotovu aplikaciju te je ovaj korak bio neizbiježan ako nije postojao `venv`

sada možemo ponoviti naredbu:

```shell
    $ pip freeze > requirements.txt
```

i možemo vidjeti da se unutar datoteke `requirements.txt` sada neophodni paketi za rad naše aplikacije:

```shell
    $ cat requirements.txt 
    asgiref==3.4.1
    backports.zoneinfo==0.2.1
    Deprecated==1.2.13
    Django==4.0
    django-crispy-forms==1.13.0
    packaging==21.3
    Pillow==8.4.0
    psycopg2>=2.8
    pyparsing==3.0.6
    redis==4.1.0
    sqlparse==0.4.2
    wrapt==1.13.3
```

Sada možemo preći na izradu `Dockerfile`-a koji će imati sljedeći oblik:

```docker
FROM python:3.8-slim-buster
ENV PYTHONUNBUFFERED=1
RUN pip install --upgrade pip

WORKDIR /app

COPY requirements.txt /app/

RUN apt-get update \
    && apt-get -y install libpq-dev gcc \
    && pip3 install psycopg2

RUN pip3 install -r requirements.txt

COPY . /app/
```

* `FROM python:3.8-slim-buster` - koristimo neku nama dovoljnu sliku pythona za rad aplikacije
* `ENV PYTHONUNBUFFERED=1` - izlaz python-a slati će se direktno u terminal tako da možemo vidjeti `Django` log-ove
* `RUN pip install --upgrade pip` - nadogradit pip
* `WORKDIR /app` - radni direktoriji
* `COPY requirements.txt /app/` - kopira prijašnje stvorene `requirements.txt` u radni direktoriji
* `RUN apt-get update \...` - u mom slučaju nije potrebno je da instaliram dodatne pakete kako bi Postrgres mogao normalno funkcijonirati
* `RUN pip3 install -r requirements.txt` - instalira sve pakete navedene u `requirements.txt`
* `COPY . /app/` - kopira sve u iz direktorija u kojem se `Dockerfile` nalazi u radni direktoriji

!!! Note
    Prije kopiranja svih datoteka u kontejner, stvorena je nova datoteka `.dockerignore` koja sadrži sve datoteke i direktorije koje želimo ignorirati. Unutar datoteke je navedeno samo virtualno okruženje, specivičnije stvoreni folder `venv`.
    ```shell
        $ cat .dockerignore
        venv
    ```

S obzirom da naša aplikacija koristi više servisa, dobra praksa je da se izbjegne izvršavanje više servisa u jednom kontejneru, tako da ćemo svaki servis pokrenuti u vlastitom kontejneru pomoću Docker Compose-a.
Krećemo tako što stvaramo novu datoteku `docker-compose.yml` sljedećeg sadržaja:

```yml
version: "3.7"
services: 
    db:
        image: postgres:14.1
        volumes:
            - ./data/db:/var/lib/postgresql/data
        environment:
            - POSTGRES_USER=postgres
            - POSTGRES_PASSWORD=postgres
            - POSTGRES_DB=postgres
    redis:
        image: "redis:alpine"
        container_name: redis
    web:
        build: .
        command: > 
            bash -c "python manage.py makemigrations &&
            python manage.py migrate &&
            python manage.py runserver 0.0.0.0:8000"
        volumes: 
            - .:/app
        ports: 
            - "8000:8000"
        environment:
            - POSTGRES_NAME=postgres
            - POSTGRES_USER=postgres
            - POSTGRES_PASSWORD=postgres
        depends_on: 
            - db
            - redis
```

Znamo da je nama potreban cache, baza podataka i nšsa Django aplikacija, stoga definiramo 3 različita servisa: `db`, `redis`, `web`. Za bazu `db` i cache `redis` navodimo slike koje ćemo preuzeti sa dockerhuba u ovom slučaju `postgres:14.1` za bazu i `image: "redis:alpine"` za cache. `volumes` nam služi kao memorija koju možemo na siguran način dijeliti između više kontejnera, dodatno imaju jako puno značajki o kojima možemo pročitati [u službenoj dokumentaciji](https://docs.docker.com/storage/volumes/ "Docker volumes"). Navodimo varijable okoline kojima ćemo se primaviti u našu bazu sa stavkom `environment`. Poželjno je spremati osjijetljive informacije u okolinu kako napadaćima nebi bile dostupne
u `settings.py`. ovdje možemo i navesti Django `SECRET_KEY` projekta koji se nalazi u `settings.py` (u ovom slučaju taj dio smo preskočili).
Primjetimo kako u `web` servisu postavljamo vrata na kojima će se aplikacija izvoditi. Dodatno koristimo `command` kako bi napravili početnu migraciju te nakon toga pokrenuli samo aplikaciju. Zadnja stavka je `depends_on` koja nam kaže da naša aplikacija ovisi o servisima `db` i `redis`, što znači da će ih aplikacija pričekati da se pokrenu prije nego što se ona sama pokrene.

Prije pokretanja kontejnera, moramo unijeti promjene u postavkama naše aplikacije. Promjene postavka baze podataka:

```py
    # mojProjekt/settings.py
    import os
    ...
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.environ.get('POSTGRES_NAME'),
            'USER': os.environ.get('POSTGRES_USER'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
            'HOST': 'db',
            'PORT': '',
        }
    }
```

Ime baze podataka, korisnika i lozinku mijenjamo na varijable koje smo postavili u okolinu dok `HOST` moramo postaviti na ime servisa onako kako smo ga nazvali u `docker-compose.yml`, u našem slučaju `db`.
Izmjene postavka cache-a:

```py
    # mojProjekt/settings.py
    ...
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': 'redis://redis:6379/0',
        }
    }
```

isto kao što smo u bazi da nam je `HOST` ime servisa iz `docker-compose.yml` datoteke tako i sada moramo promjeniti našu localhost ip adresu na ime servisa, to jest `redis`.
Ako sada pokrenemo aplikaciju vidjet ćemo da to nije još dovoljno te da nam je potrebno još promjena. Greška koja će nam se prikazati je:

```shell
    web_1    | Invalid HTTP_HOST header: '0.0.0.0:8000'. You may need to add '0.0.0.0' to ALLOWED_HOSTS.
    web_1    | Bad Request: /
    web_1    | [08/Jan/2022 19:47:52] "GET / HTTP/1.1" 400 60799
```

Moramo promjeniti dopuštene domaćine u Django postavkama:

```py
    # mojProjekt/settings.py
    ...
    ALLOWED_HOSTS = ["0.0.0.0", "127.0.0.1"]
```

Sada možemo izgraditi slike i kontejnere i pokrenuti ih:

```shell
    $ sudo docker-compose build
    ...
    Successfully built df4f2da7bd34
    Successfully tagged mmos_django_web:latest
```

vidimo da je izgradnja dobro prosla tako da sada možemo pokrenuti sve kontejnere.

```shell
    $ docker-compose up
```

Možemo vidjeti da je sve prošlo kako treba, sve slike su preuzete i svi kontejneri su pokrenuti
![Kontejneri](./kontejneri.png)
Dondatno možemo provjeriti logove `web` i `db` servisa da vidimo da sve štima i da nema greške.
Terminal `db`:

```shell
    2022-01-08 19:56:08.734 UTC [1] LOG:  starting PostgreSQL 14.1 (Debian 14.1-1.pgdg110+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 10.2.1-6) 10.2.1 20210110, 64-bit
    2022-01-08 19:56:08.734 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
    2022-01-08 19:56:08.734 UTC [1] LOG:  listening on IPv6 address "::", port 5432
    2022-01-08 19:56:08.739 UTC [1] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
    2022-01-08 19:56:08.745 UTC [25] LOG:  database system was shut down at 2022-01-08 19:53:21 UTC
    2022-01-08 19:56:08.749 UTC [1] LOG:  database system is ready to accept connections
```

Baza radi i spremna je za prihvaćanje konekcije
Terminal `web`:

```shell
    System check identified no issues (0 silenced).
    January 08, 2022 - 19:56:10
    Django version 4.0, using settings 'firs_project_django.settings'
    Starting development server at http://0.0.0.0:8000/
    Quit the server with CONTROL-C.
```

Django server se pokrenuo bez greške i možemo vidjeti da možemo otvoriti i koristiti aplikaciju. Registracija i prijava rade te možemo stvarati nove postove i izmjenjivati ih.
![Novi post](./novi_post.png)
![post](./post.png)

[Git repo sa projektom](https://github.com/Marin260/mmos_docker_project)
