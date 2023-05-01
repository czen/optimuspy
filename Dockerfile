FROM cooliron/optimuspy

RUN mkdir optimuspy
COPY . optimuspy

RUN mv opsc /optimuspy/opsc
RUN mv catch_amalgamated.cpp catch_amalgamated.hpp /optimuspy/catch2

WORKDIR /optimuspy/catch2
RUN make

WORKDIR /optimuspy
RUN pip3 install -r requirements/prod.txt
RUN python3 ./manage.py migrate
RUN mkdir -p tasks
EXPOSE 8000
