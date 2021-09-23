import numpy as np 
from CTL.tensor.tensor import Tensor 
from CTL.tensor.diagonalTensor import DiagonalTensor
import CTL.funcs.funcs as funcs
from CTL.tensor.contract.contractExp import iTEBDEvoluteFTN
from CTL.tensornetwork.tensordict import TensorDict
from CTL.funcs.decompose import SVDDecompositionWithSingularValues

class ITEBD:

    def checkGammaLabels(self, gamma):
        location = 'CTL.examples.iTEBD.ITEBD.checkGammaLabels'
        assert funcs.compareLists(gamma.labels, ['l', 'r', 'o']), funcs.errorMessage(err = '{} is not compatible with requirement for gamma tensor in ITEBD: labels ["l", "r", "o"] required.'.format(gamma), location = location)

    def getDim(self, gammaA, gammaB):
        location = 'CTL.examples.iTEBD.ITEBD.getDim'
        assert gammaA.shapeOfLabel('l') == gammaB.shapeOfLabel('r'), funcs.errorMessage(err = "dimension between left gammaA and right gammaB not compatible: {} and {}".format(gammaA.shapeOfLabel('l'), gammaB.shapeOfLabel('r')), location = location)
        assert gammaA.shapeOfLabel('r') == gammaB.shapeOfLabel('l'), funcs.errorMessage(err = "dimension between right gammaA and left gammaB not compatible: {} and {}".format(gammaA.shapeOfLabel('r'), gammaB.shapeOfLabel('l')), location = location)

        self.dimAB = gammaA.shapeOfLabel('r')
        self.dimBA = gammaA.shapeOfLabel('l')

    def getLambda(self, lbd, dim):
        if lbd is not None:
            assert lbd.shape == (dim, dim), funcs.errorMessage(err = 'shape of lambda {} is not as expected ({}, {})'.format(lbd.shape, dim, dim))
            if isinstance(lbd, DiagonalTensor):
                return lbd.copy()
            else:
                return DiagonalTensor(data = lbd, labels = ['l', 'r'])
        else:
            return DiagonalTensor(data = np.array([1] * dim), labels = ['l', 'r'])

    def checkUGenerator(self):
        location = 'CTL.examples.iTEBD.ITEBD.checkUGenerator'
        tau = 1.0
        u = self.uGenerator(tau)
        assert funcs.compareLists(u.labels, ['li', 'ri', 'lo', 'ro']), funcs.errorMessage(err = '{} is not compatible with requirement for u tensor in ITEBD: labels ["li", "ri", "lo", "ro"] required.'.format(u), location = location)
        assert (u.shapeOfLabel('li') == u.shapeOfLabel('lo')) and (u.shapeOfLabel('ri') == u.shapeOfLabel('ro')), funcs.errorMessage(err = "{} does not keep the shape of physical legs.".format(u), location = location)
        assert (u.shapeOfLabel('li') == self.gammaA.shapeOfLabel('o')) and (u.shapeOfLabel('ri') == self.gammaB.shapeOfLabel('o')), funcs.errorMessage(err = 'bond dimension of uTensor {} cannot evolute over (gammaA = {}, gammaB = {})'.format(u, self.gammaA, self.gammaB))
        assert (u.shapeOfLabel('ri') == self.gammaA.shapeOfLabel('o')) and (u.shapeOfLabel('li') == self.gammaB.shapeOfLabel('o')), funcs.errorMessage(err = 'bond dimension of uTensor {} cannot evolute over (gammaB = {}, gammaA = {})'.format(u, self.gammaB, self.gammaA))
        
    def __init__(self, chi, uGenerator, gammaA, lambdaAB = None, gammaB = None, lambdaBA = None):
        self.gammaA = gammaA.copy()
        self.dtype = self.gammaA.dtype
        self.chi = chi
        # location = 'CTL.examples.iTEBD.ITEBD.__init__'
        # gammaA / B: tensor of labels ['l', 'r', 'o']
        self.checkGammaLabels(gammaA)
        if gammaB is not None:
            self.gammaB = gammaB.copy()
            self.checkGammaLabels(gammaB)
        else:
            self.gammaB = self.gammaA.copy()

        self.getDim(gammaA = self.gammaA, gammaB = self.gammaB)
        self.lambdaAB = self.getLambda(lbd = lambdaAB, dim = self.dimAB)
        self.lambdaBA = self.getLambda(lbd = lambdaBA, dim = self.dimBA)
        self.uGenerator = uGenerator
        self.checkUGenerator()

        self.evoluteFTN = iTEBDEvoluteFTN()

        self.errors = []

    def evolute(self, tau):
        u = self.uGenerator(tau)
        # 1. contract lambdaBA, gammaA, lambdaAB, gammaB, lambdaBA, u
        # 2. SVD for gammaA', lambdaAB', gammaB'
        # 3. recover lambdaBA from gammaA' and gammaB'

        tensorDictAB = TensorDict(tensorDict = {'lambdaABl': self.lambdaAB, 'lambdaABr': self.lambdaAB, 'lambdaBA': self.lambdaBA, 'gammaA': self.gammaA, 'gammaB': self.gammaB, 'u': u})

        resTensor = self.evoluteFTN.contract(tensorDict = tensorDictAB, removeTensorTag = True)

        resMat = resTensor.toMatrix(rows = ['l', 'lo'], cols = ['r', 'ro'])

        gammaA, lambdaAB, gammaB, errorAB = SVDDecompositionWithSingularValues(a = resMat, chi = self.chi)
