package org.apache.spark.mllib.tree.loss

import main.scala.org.apache.spark.mllib.tree.model.MyModel
import org.apache.spark.mllib.tree.{NeuronUtils, Indexer, DoubleTuple}

import org.apache.spark.mllib.tree.impl.MyTreePoint
import org.apache.spark.mllib.tree.model.MyTreeEnsembleModelNew
import org.apache.spark.rdd.RDD

import scala.collection.mutable
import scala.collection.mutable.ArrayBuffer
import scala.util.Random

object MalisLoss extends MyLoss {
  val subvolume_size = 64

  override def cachedGradientAndLoss(model: MyModel,
               points: RDD[MyTreePoint],
              subsample_proportion: Double,
               save_to:String = null): (RDD[(MyTreePoint, DoubleTuple)], Double, Unit => Unit) = {
    val preds = model.predict(points.map(_.getFeatureVector))

    val (g, uncache) = NeuronUtils.cached(points.zip(preds).mapPartitionsWithIndex((_, partition) => {
      val gradsAndLosses = partition.toArray.groupBy(_._1.data.id).toArray.zipWithIndex.map { case ((id, d), _) =>
        println("Gradient for " + id + "...")
        gradAndLoss(d, subsample_proportion, if (save_to == null) null else save_to + "/" + id)
      }
      val grad = gradsAndLosses.flatMap(_._1)
      val losses = gradsAndLosses.map(_._2)
      ///grads.toIterator
      Iterator((grad, losses))
    }))

    val grad = g.flatMap(_._1)
    val loss = g.flatMap(_._2).mean()
    //make and save segs
//    if (save_to != null) {
//      segment(model, points, save_to).collect()
//    }

    (grad, loss, uncache)
  }


  def computeError(model: MyModel, data: RDD[MyTreePoint]): Double = ???

  case class Edge(point:MyTreePoint, weight:Double, from:Int, to:Int, dir:Int)

  def gradAndLoss(pointsAndPreds: Array[(MyTreePoint, DoubleTuple)], subsample_proportion:Double = 1, save_to:String) = {
    val dimensions = pointsAndPreds(0)._1.data.dimensions

    val numSamples = (dimensions._1 * dimensions._2 * subsample_proportion / (subvolume_size * subvolume_size)).toInt + 1
    val submaps = for(i <- 0 until numSamples) yield {
      val minIdx = (Random.nextInt(dimensions._1 - subvolume_size), Random.nextInt(dimensions._1 - subvolume_size))
      val maxIdx = (minIdx._1 + subvolume_size - 1, minIdx._2 + subvolume_size - 1)
      val indexer = new Indexer(dimensions, minIdx, maxIdx)
      gradAndLossForSubvolume(pointsAndPreds, indexer)
    }

//    val numSamples = (dimensions._1/subvolume_size) * (dimensions._2/subvolume_size)
//    val submaps = for(x <- 0 until dimensions._1/subvolume_size;
//                      y <- 0 until dimensions._2/subvolume_size
//                      if math.random < subsample_proportion
//    ) yield {
//        val minIdx = (x * subvolume_size, y * subvolume_size)
//        val max_x = math.min((x+1) * subvolume_size - 1, dimensions._1 - 1)
//        val max_y = math.min((y+1) * subvolume_size - 1, dimensions._2 - 1)
//        val maxIdx = (max_x, max_y)
//        val indexer = new Indexer(dimensions, minIdx, maxIdx)
//        gradAndLossForSubvolume(pointsAndPreds, indexer)
//    }

    val (grads, lossSum) = submaps.reduce((x, y) => (x._1 ++ y._1, x._2 + y._2))
    val loss = lossSum / numSamples
    if(save_to != null) {
//      val seg_save = Array.fill(pointsAndPreds.length)(0)
//      df.foreach(i => seg_save(i) = 1)
//      dt.foreach(i => seg_save(i) = 2)
//      NeuronUtils.saveSeg(save_to, "maximin_seg.raw", seg_save)
//
//      NeuronUtils.save2D(save_to, "points.raw", pointsAndPreds.map(_._1.label), dimensions)
//      NeuronUtils.save2D(save_to, "preds.raw", pointsAndPreds.map(_._2), dimensions)

      val grad_save = Array.fill[Double](pointsAndPreds.length)(0)
      grads.foreach(g => grad_save(g._1.inner_idx)=g._2.avg)
      NeuronUtils.save2D(save_to, "grads", grad_save, dimensions)
      NeuronUtils.saveText(save_to, "loss", loss.toString)
    }

    (grads, loss)
  }

  def segForSubvolume(pointsAndPreds: Array[(MyTreePoint, DoubleTuple)], indexer:Indexer):Array[Int] = {
    print("Seg for subvolume: " + indexer.minIdx + " - " + indexer.maxIdx)
    val t = System.currentTimeMillis()

    val pointsAndLabels = pointsAndPreds.map{case (p, a) => (p, p.label)} //todo: this is a complete waste

    val genSeg: Int => Int = {
      val (children, parent, getAncestor) = kruskals(pointsAndLabels, indexer, edgeFilter = _.weight == 1)
      i => if(children(i).isEmpty && parent(i)==i) -1 else getAncestor(i)
    }
    val seg = Array.tabulate[Int](indexer.size)(genSeg)
    println(" (took " + (System.currentTimeMillis() - t) + "ms)")
    seg
  }


  def gradAndLossForSubvolume(pointsAndPreds: Array[(MyTreePoint, DoubleTuple)], indexer:Indexer) = {
    val seg = segForSubvolume(pointsAndPreds, indexer)
    val n = Math.pow(subvolume_size,2)
    val scaleFactor = 2d / (n * (n-1))// (nC2)^-1

    print("Grad for subvolume: " + indexer.minIdx + " - " + indexer.maxIdx)
    val t = System.currentTimeMillis()

    var loss = 0d
    //val gradients = new ArrayBuffer[(MyTreePoint, DoubleTuple)]()

    val gradients = Array.fill(indexer.size)(DoubleTuple.Zero)

    def innerFunc(edge:Edge, descendants:Int => Seq[Int], ancFrom:Int, ancTo:Int) = {
      //println("Adding wedge with weight " + edge.weight)

      //val trueAffs = pointsAndPreds(indexer.innerToOuter(edge.to))._1.label
      val predAffs = pointsAndPreds(indexer.innerToOuter(edge.to))._2
      val aff:Double = predAffs(edge.dir)

      val descFrom = descendants(ancFrom).groupBy(seg)
      val descTo = descendants(ancTo).groupBy(seg)
      var nPos = 0
      var nNeg = 0
      for((segFrom, subsetFrom) <- descFrom;
          (segTo, subsetTo) <- descTo) {
        if(segFrom == segTo && segFrom != -1) nPos += subsetFrom.size * subsetTo.size
        else nNeg += subsetFrom.size * subsetTo.size
      }
      val del = (nPos - aff*(nNeg + nPos)) * scaleFactor
      loss += (nPos * (1-aff)*(1-aff) + nNeg * aff*aff) * scaleFactor

      //gradients.append(edge.point -> DoubleTuple.oneHot(edge.dir, del))
      val innerIdx = indexer.outerToInner(edge.point.inner_idx)
      gradients(innerIdx) = gradients(innerIdx) + DoubleTuple.oneHot(edge.dir, del)
    }

    kruskals(pointsAndPreds, indexer, innerFunc = innerFunc)

//    val grad = gradients.groupBy(_._1).map{ case (p, s) =>
//      p -> s.map(_._2).reduce(_+_)
//    }

    val grad = Array.tabulate(indexer.size)(i =>
      (pointsAndPreds(indexer.innerToOuter(i))._1, gradients(i))
    )

    println(" (took " + (System.currentTimeMillis() - t) + "ms)")
    (grad, loss)

  }

  def kruskals(pointsAndAffs: Array[(MyTreePoint, DoubleTuple)], indexer:Indexer, edgeFilter:Edge => Boolean = _ => true,
               innerFunc:(Edge, Int=>Seq[Int], Int, Int) => Unit = (_, _, _, _) => {})
  :(Array[IndexedSeq[Int]], Array[Int], Int => Int) = {

    val edgeList = (0 until indexer.size).flatMap( i => { // i is an INNER index
      val (point, affs) = pointsAndAffs(indexer.innerToOuter(i))
      val multi = indexer.innerToMulti(i)
      val l1 = if(multi._1 >= indexer.innerDimensions._1-1) List()
               else List(Edge(point, affs._1, i, i + indexer.innerSteps._1, 1))

      val l2 = if(multi._2 >= indexer.innerDimensions._2-1) List()
               else List(Edge(point, affs._2, i, i + indexer.innerSteps._2, 2))

      l1 ++ l2
    })

    val edges = new mutable.PriorityQueue[Edge]()(Ordering.by(_.weight)) //Order by weight DESCENDING
    edges ++= edgeList.filter(edgeFilter)

    val parent = Array.tabulate[Int](indexer.size)(i => i)
    val children = Array.fill[IndexedSeq[Int]](indexer.size){ IndexedSeq[Int]() }
    def getAncestor(nodeIdx:Int):Int = {
        if(parent(nodeIdx) == nodeIdx) nodeIdx else getAncestor(parent(nodeIdx))
    }

    val descendants = Array.tabulate[Vector[Int]](indexer.size){ i => Vector(i)}
    //def getDescendants(nodeIdx:Int):IndexedSeq[Int] = children(nodeIdx).flatMap(getDescendants) :+ nodeIdx

    var numEdges = 0
    while(numEdges < indexer.size-1 && edges.nonEmpty) {
      val edge = edges.dequeue()
      val ancFrom = getAncestor(edge.from)
      val ancTo = getAncestor(edge.to)
      if(ancFrom != ancTo) {
        innerFunc(edge, descendants, ancFrom, ancTo)
        if(descendants(ancFrom).size > descendants(ancTo).size) {
          parent(ancTo) = ancFrom
          children(ancFrom) = children(ancFrom) :+ ancTo
          descendants(ancFrom) = descendants(ancFrom) ++ descendants(ancTo)
          descendants(ancTo) == Vector[Int]()
        } else {
          parent(ancFrom) = ancTo
          children(ancTo) = children(ancTo) :+ ancFrom
          descendants(ancTo) = descendants(ancTo) ++ descendants(ancFrom)
          descendants(ancFrom) == Vector[Int]()
        }
        numEdges = numEdges + 1
      }
    }

    (children, parent, getAncestor)
  }
}


