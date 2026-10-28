package edu.DProvDB.Utils

import breeze.stats.distributions.{RandBasis, ThreadLocalRandomGenerator}
import org.apache.commons.math3.random.RandomGenerator

/** Avoid ephemeral ThreadLocal entries in the single-threaded reproduction. */
object RandomBasis {
  private val direct = scala.sys.env.get("DPROVDB_PROFILE").contains("paper")

  def fromGenerator(generator: => RandomGenerator): RandBasis = {
    if (direct) new RandBasis(generator)
    else new RandBasis(new ThreadLocalRandomGenerator(generator))
  }
}
