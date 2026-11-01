package edu.Experiments

import edu.DProvDB.{AccuracyState, ProvenanceState, State}
import edu.DProvDB.Model.View
import edu.DProvDB.Utils.MetricUtils
import java.io.{File, PrintWriter}

/** Isolated extension harness; no change to the original Experiment or mechanisms. */
object FiveDatasets {
  final class ExtensionState extends State {
    override def setupViews(): List[View] = {
      viewManager.setState(this)
      if (_views == null) {
        val result = time { viewManager.setupPlainViews() }
        _views = result._1
        _viewSetupTime = result._2
      } else _views.foreach(_.refresh)
      _views
    }
  }
  val datasets = Map(
    "bank" -> (45211, "age"), "credit" -> (30000, "limit_bal"),
    "shoppers" -> (12330, "productrelated"),
    "diabetes" -> (101766, "num_lab_procedures"),
    "covertype" -> (581012, "elevation"))
  def main(args: Array[String]): Unit = {
    require(args.length == 3, "FiveDatasets DATASET OUTPUT_DIRECTORY smoke|formal")
    val dataset = args(0)
    require(datasets.contains(dataset))
    require(Set("smoke", "formal")(args(2)))
    require(scala.sys.env.get("DPROVDB_PROFILE").contains("paper"), "Use the validated single-thread RNG adapter")
    val smoke = args(2) == "smoke"
    val out = new File(args(1))
    require(!out.exists(), "Refusing to overwrite output directory")
    require(out.mkdirs())
    java.lang.System.setProperty("dp.elastic_sensitivity.check_bins_for_release", "false")
    java.lang.System.setProperty("db.use_dummy_database", "false")
    java.lang.System.setProperty("db.driver", "org.postgresql.Driver")
    java.lang.System.setProperty("db.url", "jdbc:postgresql://localhost:5432/" + dataset)
    java.lang.System.setProperty("db.username", scala.sys.env("DPROVDB_DB_USER"))
    java.lang.System.setProperty("db.password", scala.sys.env("DPROVDB_DB_PASSWORD"))
    java.lang.System.setProperty("schema.config.path", "extensions/five-datasets/shared/schema.yaml")
    val state = new ExtensionState
    state.setupDB(dataset, "records")
    state.viewManager.setBucketNum(50)
    state.setupViews()
    require(state._views.size == 5)
    state._views.foreach(v => require(v.histogramView.values.sum == datasets(dataset)._1.toDouble,
      "Histogram must cover every input record"))
    val audit = new PrintWriter(new File(out, "histograms.csv"))
    audit.println("attribute,bin,count")
    state._views.foreach(v => (0 until 50).foreach(i => audit.println(s"${v._attrs.head},$i,${v.histogramView(i.toString)}")))
    audit.close()
    val viewMs = state._viewSetupTime
    val writer = new PrintWriter(new File(out, "results.csv"))
    writer.println("dataset,phase,mechanism,scheduler,budget,run,seed,utility,answered_low,answered_high,dcfg,ndcfg,epsilon,epsilon_low,epsilon_high,requested_variance_mean,execution_ms,noncached,cache_hits,candidate_queries,per_query_delta,total_delta,view_setup_ms,threshold,workload_per_analyst")
    val runs = if (smoke) 1 to 1 else 1 to 4
    var completed = 0
    try {
      for (phase <- List("RRQ", "BFS"); run <- runs;
           budget <- (if (phase == "BFS") List(200.0) else if (smoke) List(0.4) else List(0.4, 0.8, 1.6, 3.2, 6.4));
           scheduler <- (if (phase == "BFS") List("BFS") else List("round-robin", "random"));
           mechanism <- (if (phase == "BFS") List("aGM", "baseline", "Chorus", "ChorusP") else List("aGM", "baseline", "PrivateSQL", "Chorus", "ChorusP"))) {
        state.setupViews() // refresh noisy state only; never reuse a prior mechanism's private synopsis
        state.setCurRun(run)
        state.setOverallBudget(budget)
        val provenance = mechanism match {
          case "aGM" => ProvenanceState("dynamic", "fixed-aGM")
          case "baseline" => ProvenanceState("dynamic", "fixed-normalized")
          case _ if phase == "BFS" => ProvenanceState("dynamic", "fixed-normalized")
          case _ => ProvenanceState("static", "fixed-normalized")
        }
        state.setProvenanceState(provenance)
        state.setDelta(1e-9, 1e-5)
        state.setupAnalysts(List(1, 4))
        val threshold = math.max(5.0, datasets(dataset)._1 * 0.01)
        val workload = if (smoke) 40 else 4000
        if (phase == "RRQ") state.setupAnalystWorkload("RRQ", workload, AccuracyState("increasing", 3000, increasingStep = 1))
        else state.setupEQW("EQW", List(datasets(dataset)._2), 2.0, threshold, 5, AccuracyState("increasing", 25000, increasingStep = 100))
        state.setMechanism(mechanism, "basic")
        state.setScheduler(scheduler, false)
        state.setLogger("info")
        val system = new edu.DProvDB.System
        system.setup(state)
        val start = java.lang.System.nanoTime()
        system.execute()
        val elapsed = (java.lang.System.nanoTime() - start) / 1e6
        val utility = MetricUtils.utility(state._analysts)
        val breakdown = MetricUtils.getUtilityBreakDown(state._analysts)
        val dcfg = MetricUtils.DCFG(state._analysts)
        val ndcfg = if (utility == 0) "" else (dcfg / utility).toString
        val req = if (utility == 0) "" else system.avgAccuracy.toString
        val candidates = if (phase == "RRQ") workload * 2 else state._workloadSize // already multiplied by analysts in setupEQW
        val values = List(dataset, phase, mechanism, scheduler, budget, run, state._randomnessSeed,
          utility, breakdown(0), breakdown(1), dcfg, ndcfg, system.accountant,
          system.analystsAccountant(0), system.analystsAccountant(1), req, elapsed,
          system.nonCachedQueryCounter, utility - system.nonCachedQueryCounter, candidates,
          state._per_query_delta, state._delta, viewMs, if (phase == "BFS") threshold else "", if (phase == "RRQ") workload else "")
        writer.println(values.mkString(",")); writer.flush()
        completed += 1
        println(s"EXTENSION_COMPLETE dataset=$dataset phase=$phase method=$mechanism budget=$budget scheduler=$scheduler run=$run utility=$utility epsilon=${system.accountant} count=$completed")
      }
    } finally writer.close()
    require(completed == (if (smoke) 14 else 216))
    println(s"EXTENSION_SUCCESS dataset=$dataset records=$completed")
  }
}
