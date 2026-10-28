package edu.DProvDB.Utils

import breeze.stats.distributions.{Gaussian, RandBasis, ThreadLocalRandomGenerator}
import org.apache.commons.math3.random.MersenneTwister
import org.junit.Assert.assertEquals
import org.junit.Test

class RandomBasisTest {
  @Test def directAndThreadLocalGeneratorsHaveIdenticalSeededDraws(): Unit = {
    for (seed <- 0L until 100L) {
      val direct = Gaussian(7.5, 3.0)(new RandBasis(new MersenneTwister(seed)))
      val wrapped = Gaussian(7.5, 3.0)(new RandBasis(new ThreadLocalRandomGenerator(new MersenneTwister(seed))))
      for (_ <- 0 until 20) assertEquals(wrapped.draw(), direct.draw(), 0.0)
    }
  }
}
