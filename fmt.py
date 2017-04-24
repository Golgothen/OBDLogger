class FMT():

    def __init__(self, **kwargs)
        # Set the defaults
        self.length = 9
        self.precision = 2
        self.type = 'f'
        self.alignment = '>'
        self.commas = True
        self.truncate = True

        for k in kwargs:
            if k == 'LENGTH':
                self.length = kwargs[k]
            if k == 'PRECISION':
                self.precision = kwargs[k]
            if k == 'TYPE':
                self.type = kwargs[k]
            if k == 'ALIGNMENT':
                self.alignment = kwargs[k]
            if k == 'COMMAS':
                self.commas = kwargs[k]
            if k == 'TRUNCATE':
                self.truncate = kwargs[k]

    @property
    def fmtstr(self):
        str = '{:'
        if self.type == 's':
            self.commas = False
            str += self.alignment
            self.precision = None
        else:
            self.commas = commas
            self.precision = precision
            self.alignment = None
        str += '{}'.format(self.length)
        if self.commas:
            str+=','
        if self.precision is not None:
            str += '.{}'.format(self.precision)
        if self.type != 's':
            str+='{}'.format(self.type)
        str += '}'
        return str

    def __call__(self, v):
        tmp = self.fmtstr.format(v)
        print(self.fmtstr)
        if len(tmp) > self.length\
           and self.precision is not None\
           and self.truncate:                                 # String is too long.  See if we can drop some precision to get it to fit
            c = self.commas                                   # Store commas so we can reset it
            p = self.precision                                # store the presisopn so we can reset it later
            while len(tmp) > self.length \
              and self.precision > 0:
                self.precision -= 1
                print(self.fmtstr)
                tmp = self.fmtstr.format(v)
            # Still too long and no more precision to remove.
            # if the number contains commas, try removing those next
            if self.precision == 0 and \
               len(tmp) > self.length and \
               ',' in tmp:
                self.commas = False
                tmp = self.fmtstr.format(v)
            self.precision = p
            self.commas = c
        return tmp
