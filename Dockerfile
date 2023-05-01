FROM cooliron/optimuspy

RUN git clone https://github.com/COOLIRON2311/optimuspy.git

RUN mv opsc /optimuspy/opsc
RUN mv catch_amalgamated.cpp catch_amalgamated.hpp /optimuspy/catch2

WORKDIR /optimuspy/catch2
RUN make

WORKDIR /optimuspy
RUN curl https://gist.githubusercontent.com/COOLIRON2311/e7adc804d78c1cd31c933e3f622512f2/raw/75ff26c97c3cf51efbfc87b0e3d7a0330157dbe5/.env -o .env
RUN pip3 install -r requirements/prod.txt
RUN python3 ./manage.py migrate
RUN mkdir tasks
EXPOSE 8000
