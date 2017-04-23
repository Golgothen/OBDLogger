class FMT():

    def __init__(self, length = 9, precision = 2, type = 'f', commas = True, truncate = True):
        self.length = length
        self.precision = precision
        self.type = type
        self.commas = commas
        self.truncate = truncate

    @property
    def fmtstr(self):
        str = '{:'
        if self.type == '':
            str += '>'
        str += '{}'.format(self.length)
        if self.commas:
            str+=','
        if self.precision > 0:
            str += '.{}{}'.format(self.precision, self.type)
        str += '}'
        return str

    def __call__(self, v):
        tmp = self.fmtstr.format(v)
        if len(tmp) > self.length and self.truncate:          # String is too long.  See if we can drop some precision to get it to fit
            c = self.commas                               # Store commas so we can reset it
            p = self.precision                                # store the presisopn so we can reset it later
            while len(tmp) > self.length \
              and self.precision > 0:
                self.precision -= 1
                tmp = self.fmtstr
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
